"""Analysis pipeline: deterministic doc type -> (live LLM | golden) -> deterministic quote verification.

Medical boundary: imaging reports and vaccination records never yield recommendations, whatever the model says.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.contracts.documents import (
    DocumentAnalysis,
    DocumentType,
    ExtractedPerson,
    Recommendation,
    RecommendationCategory,
)
from app.core.llm import get_llm
from app.services.documents import goldens
from app.services.documents.verify import verify_recommendations

log = logging.getLogger(__name__)

PROMPT = (Path(__file__).parent / "prompts" / "extract_de.md").read_text(encoding="utf-8")
BENEFIT_IDS = {"pflegegeld", "reha_onko", "fsw_mobile_pflege", "pflegeberatung", "krankentransport",
               "fahrtkostenzuschuss", "rezeptgebuehrenbefreiung", "hauskrankenpflege"}
NO_RECOMMENDATION_TYPES = {DocumentType.imaging_report, DocumentType.vaccination_record}
IMAGING_NOTICE_DE = ("Dies ist ein Befund der bildgebenden Diagnostik. Ich interpretiere keine Befunde – "
                     "bitte besprechen Sie das Ergebnis mit Ihrer Ärztin bzw. Ihrem Arzt.")


def user_message(pages: list[str]) -> str:
    return "\n\n".join(f"=== Seite {i} ===\n{t}" for i, t in enumerate(pages, 1))


def parse_llm_json(raw: dict) -> tuple[ExtractedPerson, list[Recommendation], list[str]]:
    """Tolerant mapping of model JSON onto contract types. Invalid entries are dropped, never repaired."""
    person_raw = raw.get("person") or {}
    person = ExtractedPerson(**{k: (str(v) if v is not None else None) for k, v in person_raw.items()
                                if k in ExtractedPerson.model_fields})
    recs: list[Recommendation] = []
    for i, r in enumerate(raw.get("recommendations") or [], 1):
        try:
            cat = r.get("category", "other")
            recs.append(Recommendation(
                id=f"r{i}",
                text_de=str(r["text_de"]),
                quote=str(r["quote"]),
                page=int(r["page"]),
                category=cat if cat in RecommendationCategory.__members__ else RecommendationCategory.other,
                related_benefit_ids=[b for b in (r.get("related_benefit_ids") or []) if b in BENEFIT_IDS],
            ))
        except (KeyError, TypeError, ValueError):
            continue
    tasks = [str(t) for t in (raw.get("open_tasks") or []) if isinstance(t, str | int | float)]
    return person, recs, tasks


def _live(document_id: str, filename: str, doc_type: DocumentType, pages: list[str]) -> DocumentAnalysis:
    raw = get_llm().json(PROMPT, user_message(pages))
    person, recs, tasks = parse_llm_json(raw)
    return DocumentAnalysis(document_id=document_id, filename=filename, doc_type=doc_type, pages=len(pages),
                            person=person, recommendations=recs, open_tasks=tasks, extraction_mode="live")


def from_golden(golden: dict, document_id: str, filename: str | None = None) -> DocumentAnalysis:
    a = DocumentAnalysis(document_id=document_id, **golden["analysis"])
    return a.model_copy(update={"filename": filename or a.filename, "extraction_mode": "golden"})


def analyze_pdf(document_id: str, filename: str, sha: str, doc_type: DocumentType, pages: list[str]) -> DocumentAnalysis:
    golden = goldens.by_sha(sha)
    analysis: DocumentAnalysis | None = None
    if doc_type not in NO_RECOMMENDATION_TYPES and get_llm().live:
        try:
            analysis = _live(document_id, filename, doc_type, pages)
        except Exception as e:  # noqa: BLE001 — network / auth / JSON errors -> golden fallback
            log.warning("live extraction failed (%s), falling back to golden", e)
    if analysis is None and golden:
        analysis = from_golden(golden, document_id, filename)
    if analysis is None:
        analysis = DocumentAnalysis(document_id=document_id, filename=filename, doc_type=doc_type, pages=len(pages),
                                    person=ExtractedPerson(), recommendations=[], open_tasks=[], extraction_mode="fake")
    # Deterministic doc type wins over model/golden; boundary types never carry recommendations.
    analysis = analysis.model_copy(update={"doc_type": doc_type, "pages": len(pages)})
    return enforce_boundary(verify(analysis, pages))


def verify(analysis: DocumentAnalysis, pages: list[str]) -> DocumentAnalysis:
    kept, dropped = verify_recommendations(analysis.recommendations, pages)
    if dropped:
        log.info("dropped unverified recommendations %s for %s", dropped, analysis.document_id)
    return analysis.model_copy(update={"recommendations": kept})


def enforce_boundary(analysis: DocumentAnalysis) -> DocumentAnalysis:
    if analysis.doc_type in NO_RECOMMENDATION_TYPES:
        update: dict = {"recommendations": [], "open_tasks": []}
        if analysis.doc_type == DocumentType.imaging_report:
            update["notice_de"] = IMAGING_NOTICE_DE
        return analysis.model_copy(update=update)
    return analysis
