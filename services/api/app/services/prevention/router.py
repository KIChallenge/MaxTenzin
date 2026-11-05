"""prevention — e-Impfpass import (deterministic parser) + Vorsorge/Impf-Hinweise (deterministic rules)."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.contracts.documents import DocumentType
from app.contracts.identity import Scope
from app.contracts.prevention import PreventionOverview, VaccinationEntry
from app.core.auth import Context, require
from app.core.db import now_iso, store
from app.services.documents import goldens, storage
from app.services.documents.pdf import detect_doc_type, page_texts
from app.services.prevention.engine import evaluate
from app.services.prevention.impfpass import parse_impfpass

router = APIRouter(prefix="/api/prevention", tags=["prevention"])

VACCINATIONS = "vaccinations"  # per subject id: {"subject_id", "source_document_id", "imported_at", "vaccinations": [...]}


def _stored_vaccinations(subject_id: str) -> tuple[list[VaccinationEntry], str | None]:
    doc = store.get(VACCINATIONS, subject_id)
    if not doc:
        return [], None
    return [VaccinationEntry(**v) for v in doc["vaccinations"]], doc.get("source_document_id")


def _overview(ctx: Context, as_of: date, family_history: list[str] | None = None) -> PreventionOverview:
    vaccinations, source_doc = _stored_vaccinations(ctx.subject.id)
    items, rule_ids = evaluate(ctx.subject, vaccinations, as_of, family_history)
    ctx.rule_ids.extend(rule_ids)
    ctx.cite(*sorted({s.label for i in items for s in i.sources}))
    if source_doc:
        ctx.cite(f"e-Impfpass ({source_doc})")
    vaccinations = sorted(vaccinations, key=lambda v: (v.disease, v.date), reverse=True)
    return PreventionOverview(subject_id=ctx.subject.id, as_of=as_of.isoformat(), vaccinations=vaccinations, items=items)


def _as_of(value: str | None) -> date:
    try:
        return date.fromisoformat(value) if value else date.today()
    except ValueError as e:
        raise HTTPException(422, "as_of muss ein Datum im Format JJJJ-MM-TT sein.") from e


@router.get("/overview", response_model=PreventionOverview, summary="Vaccination history + due prevention items")
def overview(as_of: str | None = Query(None, description="Stichtag (ISO date), default today"),
             family_history: list[str] | None = Query(
                 None, description="Erkrankungen in der Familie laut eigener Angabe, z. B. darmkrebs, brustkrebs, "
                                   "diabetes, herz_kreislauf → passende Programme werden als besonders relevant "
                                   "erklärt (keine Risikoeinschätzung)"),
             ctx: Context = Depends(require(Scope.view_health_prevention))):
    return _overview(ctx, _as_of(as_of), family_history)


@router.post("/import/{document_id}", response_model=PreventionOverview, summary="Import vaccinations from an uploaded e-Impfpass PDF")
def import_impfpass(document_id: str, as_of: str | None = Query(None, description="Stichtag (ISO date), default today"),
                    ctx: Context = Depends(require(Scope.view_health_prevention))):
    meta = storage.get_meta(document_id)
    if meta and meta.get("owner_id") != ctx.subject.id:
        raise HTTPException(404, "Dokument nicht gefunden")
    data = storage.load_pdf(document_id) if meta else None
    if data:
        pages = page_texts(data)
        if detect_doc_type(pages, meta.get("filename", "")) != DocumentType.vaccination_record:
            raise HTTPException(422, "Das Dokument ist kein e-Impfpass.")
        vaccinations = parse_impfpass(pages)
    elif (g := goldens.by_demo_id(document_id)) and g.get("demo_subject_id") == ctx.subject.id and "vaccinations" in g:
        vaccinations = [VaccinationEntry(**v) for v in g["vaccinations"]]  # demo e-Impfpass known by its golden
    else:
        raise HTTPException(404, "Dokument nicht gefunden")
    if not vaccinations:
        raise HTTPException(422, "Im Dokument wurden keine Impfeinträge erkannt.")
    store.put(VACCINATIONS, ctx.subject.id, {
        "subject_id": ctx.subject.id, "source_document_id": document_id, "imported_at": now_iso(),
        "vaccinations": [v.model_dump() for v in vaccinations],
    }, subject_id=ctx.subject.id)
    ctx.rule_ids.append("prevention.impfpass_parser.v1")
    return _overview(ctx, _as_of(as_of))
