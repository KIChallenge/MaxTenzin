"""Explicit demo seeding: copy the fictional demo PDFs from RAW_DATA_DIR/Befunde into var/uploads under their
golden demo ids and import Stefan's e-Impfpass. Never commits anything; var/ is gitignored.

    cd services/api && RAW_DATA_DIR=/path/to/docs uv run python -m app.services.documents.seed_demo
"""

from __future__ import annotations

from app.contracts.documents import DocumentSummary
from app.core.config import get_settings
from app.core.db import now_iso, store
from app.services.documents import goldens, storage
from app.services.documents.extract import analyze_pdf
from app.services.documents.pdf import detect_doc_type, page_texts, sha256
from app.services.prevention.impfpass import parse_impfpass
from app.services.prevention.router import VACCINATIONS


def seed(skip: set[str] | None = None) -> list[str]:
    """skip: demo document ids NOT to seed (live demo: Anna's discharge letter is uploaded as photos on stage)."""
    befunde = get_settings().raw_data_dir / "Befunde"
    seeded = []
    for g in goldens.all_goldens():
        if g["demo_document_id"] in (skip or set()):
            store.put(goldens.HIDDEN, g["demo_document_id"], {"document_id": g["demo_document_id"]},
                      subject_id=g["demo_subject_id"])
            continue
        src = befunde / g["source_filename"]
        if not src.exists():
            continue
        data = src.read_bytes()
        if sha256(data) != g["sha256"]:
            print(f"skip {src.name}: content differs from golden")
            continue
        doc_id, subject = g["demo_document_id"], g["demo_subject_id"]
        pages = page_texts(data)
        doc_type = detect_doc_type(pages, src.name)
        storage.save_pdf(doc_id, data)
        summary = DocumentSummary(document_id=doc_id, filename=src.name, doc_type=doc_type,
                                  uploaded_at=now_iso(), owner_id=subject)
        store.put(storage.DOCS, doc_id, {**summary.model_dump(), "sha256": g["sha256"], "pages": len(pages)},
                  subject_id=subject)
        analysis = analyze_pdf(doc_id, src.name, g["sha256"], doc_type, pages)
        store.put(storage.ANALYSES, doc_id, analysis.model_dump(mode="json"), subject_id=subject)
        if "vaccinations" in g:
            store.put(VACCINATIONS, subject, {
                "subject_id": subject, "source_document_id": doc_id, "imported_at": now_iso(),
                "vaccinations": [v.model_dump() for v in parse_impfpass(pages)],
            }, subject_id=subject)
        seeded.append(f"{doc_id} ({subject}, {doc_type.value}, {len(analysis.recommendations)} recs)")
    return seeded


def seed_live_start() -> list[str]:
    """Live demo start state (DEMO_LIVE=1): Maria may NOT yet read documents or prepare applications for Anna
    (Anna grants both on stage), and Stefan has chosen English in his preferences."""
    from app.seed.loader import OVERRIDES, delegations_for

    d = next(x for x in delegations_for("anna") if x.id == "del-anna-maria")
    scopes = [str(getattr(s, "value", s)) for s in d.scopes if str(getattr(s, "value", s))
              not in ("read_documents", "prepare_applications")]
    store.put(OVERRIDES, d.id, {"scopes": scopes}, subject_id="anna")
    store.put("preferences", "stefan", {"language": "en", "plain_language": False, "detail": "normal",
                                        "daypart": "any", "near_home": True, "accessible": False, "voice": False},
              subject_id="stefan")
    return [f"Vollmacht Anna→Maria für den Demo-Start: {', '.join(scopes)}", "Stefan: Sprache Englisch"]


if __name__ == "__main__":
    import os

    skip = {s.strip() for s in os.environ.get("SEED_SKIP_DOCS", "").split(",") if s.strip()}
    for line in seed(skip) or ["nothing seeded — RAW_DATA_DIR/Befunde not found"]:
        print(line)
    if os.environ.get("DEMO_LIVE"):
        for line in seed_live_start():
            print(line)
