"""forms — one schema, two clients (wizard + chat), filled OFFICIAL PDF as draft (owner: WS-F)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.contracts.documents import DocumentAnalysis
from app.contracts.forms import FieldPatch, FormDefinition, FormSession, NextQuestions
from app.contracts.identity import Scope
from app.core.auth import Context, require
from app.core.db import store
from app.services.forms import service
from app.services.forms.pdf import render_pdf
from app.services.forms.service import FormPreview
from app.services.forms.spec import load_specs

router = APIRouter(prefix="/api/forms", tags=["forms"])


def _cite_form(ctx: Context, form_id: str) -> None:
    spec = service.spec_or_404(form_id)
    ctx.cite(f"{spec.title_de} – {spec.form_version}")


@router.get("", response_model=list[FormDefinition], summary="Available form definitions")
def definitions(ctx: Context = Depends(require())):
    return [s.to_contract() for s in load_specs().values()]


@router.get("/definitions/{form_id}", response_model=FormDefinition, summary="One form definition (wizard + agent)")
def definition(form_id: str, ctx: Context = Depends(require())):
    return service.spec_or_404(form_id).to_contract()


@router.post("/definitions/{form_id}/sessions", response_model=FormSession, summary="Start a prefilled form session")
def start(form_id: str, document_id: str | None = Query(None, description="Optional analysed document for prefill"),
          ctx: Context = Depends(require(Scope.prepare_applications))):
    spec = service.spec_or_404(form_id)
    analysis = None
    if document_id:
        if Scope.read_documents not in ctx.scopes:
            raise HTTPException(403, "Fehlende Berechtigung 'read_documents' für die Vorbefüllung aus Dokumenten.")
        data = store.get("document_analyses", document_id)
        if not data:
            raise HTTPException(404, "Dokumentanalyse nicht gefunden – bitte das Dokument zuerst analysieren.")
        owner = (store.get("documents", document_id) or {}).get("owner_id")
        if owner and owner != ctx.subject.id:
            raise HTTPException(404, "Dokumentanalyse nicht gefunden.")
        analysis = DocumentAnalysis(**data)
        ctx.cite(analysis.filename)
    _cite_form(ctx, form_id)
    return service.start_session(spec, ctx.subject, ctx.actor, analysis)


@router.get("/sessions/{session_id}", response_model=FormSession, summary="Current session values")
def get_session(session_id: str, ctx: Context = Depends(require(Scope.prepare_applications))):
    return service.load_session(session_id, ctx.subject.id)


@router.get("/sessions/{session_id}/next-questions", response_model=NextQuestions,
            summary="Only missing required fields (optionally also recommended ones)")
def next_questions(session_id: str, include_optional: bool = Query(False),
                   ctx: Context = Depends(require(Scope.prepare_applications))):
    sess = service.load_session(session_id, ctx.subject.id)
    return service.next_questions(service.spec_or_404(sess.form_id), sess, include_optional)


@router.patch("/sessions/{session_id}", response_model=FormSession, summary="Set field values (wizard or agent)")
def patch(session_id: str, body: FieldPatch, ctx: Context = Depends(require(Scope.prepare_applications))):
    sess = service.load_session(session_id, ctx.subject.id)
    return service.apply_patch(service.spec_or_404(sess.form_id), sess, body.values, body.confirm)


@router.get("/sessions/{session_id}/preview", response_model=FormPreview,
            summary="Review step: label, value and source of every filled field")
def preview(session_id: str, ctx: Context = Depends(require(Scope.prepare_applications))):
    sess = service.load_session(session_id, ctx.subject.id)
    _cite_form(ctx, sess.form_id)
    return service.preview(service.spec_or_404(sess.form_id), sess)


@router.post("/sessions/{session_id}/render", summary="Render filled official PDF (draft – never submitted)",
             response_class=Response, responses={200: {"content": {"application/pdf": {}}}})
def render(session_id: str, ctx: Context = Depends(require(Scope.prepare_applications))):
    sess = service.load_session(session_id, ctx.subject.id)
    spec = service.spec_or_404(sess.form_id)
    _cite_form(ctx, sess.form_id)
    pdf = render_pdf(spec, service.relevant_values(spec, sess))
    sess.status = "rendered"
    service.save(sess)
    filename = f"{spec.form_id}_ENTWURF.pdf"
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/definitions/{form_id}/template", summary="Blank official form PDF (as published by the Träger)")
def template(form_id: str, ctx: Context = Depends(require())):
    from fastapi.responses import FileResponse

    from app.core.config import get_settings

    service.spec_or_404(form_id)
    path = get_settings().knowledge_dir / "forms" / "templates" / f"{form_id}.pdf"
    if not path.exists():
        raise HTTPException(404, "Formularvorlage nicht vorhanden")
    return FileResponse(path, media_type="application/pdf", filename=f"{form_id}.pdf",
                        content_disposition_type="inline")


@router.get("/brochures/serviceratgeber", summary="ÖGK Serviceratgeber 2026 PDF (only if the raw data folder is present)")
def serviceratgeber(ctx: Context = Depends(require())):
    from fastapi.responses import FileResponse

    from app.core.config import get_settings

    p = get_settings().raw_data_dir / "Leistungskataloge" / "Serviceratgeber-2026_Broschuere_A5_OEAM_99-19_klein_korr.pdf"
    if not p.exists():
        raise HTTPException(404, "Broschüre lokal nicht vorhanden (Rohdaten nicht eingebunden)")
    return FileResponse(p, media_type="application/pdf", filename="OEGK-Serviceratgeber-2026.pdf",
                        content_disposition_type="inline")
