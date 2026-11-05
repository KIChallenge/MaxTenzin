"""forms — one schema, two clients (wizard + chat). STUB (owner: WS-F)."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.contracts.forms import FieldPatch, FieldValue, FormDefinition, FormSession, NextQuestions
from app.contracts.identity import Scope
from app.core.auth import Context, require
from app.core.config import get_settings
from app.core.db import now_iso, store
from app.fixtures import PAL080_DEF, PAL080_SESSION

router = APIRouter(prefix="/api/forms", tags=["forms"])


@router.get("", response_model=list[FormDefinition], summary="Available form definitions")
def definitions(ctx: Context = Depends(require())):
    return [PAL080_DEF]  # STUB


@router.get("/definitions/{form_id}", response_model=FormDefinition)
def definition(form_id: str, ctx: Context = Depends(require())):
    if form_id != PAL080_DEF.form_id:
        raise HTTPException(404, "Formular nicht gefunden")
    return PAL080_DEF


@router.post("/definitions/{form_id}/sessions", response_model=FormSession, summary="Start a prefilled form session")
def start(form_id: str, ctx: Context = Depends(require(Scope.prepare_applications))):
    sess = PAL080_SESSION.model_copy(update={"subject_id": ctx.subject.id, "actor_id": ctx.actor.id, "updated_at": now_iso()})
    store.put("form_sessions", sess.id, sess.model_dump(), subject_id=ctx.subject.id)
    return sess  # STUB: fixed id/prefill


@router.get("/sessions/{session_id}", response_model=FormSession)
def get_session(session_id: str, ctx: Context = Depends(require(Scope.prepare_applications))):
    data = store.get("form_sessions", session_id)
    if not data:
        raise HTTPException(404, "Sitzung nicht gefunden")
    return data


@router.get("/sessions/{session_id}/next-questions", response_model=NextQuestions, summary="Only missing required fields")
def next_questions(session_id: str, ctx: Context = Depends(require(Scope.prepare_applications))):
    sess = FormSession(**(store.get("form_sessions", session_id) or PAL080_SESSION.model_dump()))
    missing = [f for f in PAL080_DEF.fields if f.required and sess.values.get(f.id, FieldValue(value=None)).value in (None, "")]
    req = [f for f in PAL080_DEF.fields if f.required]
    return NextQuestions(session_id=session_id, questions=missing, progress=1 - len(missing) / max(1, len(req)))


@router.patch("/sessions/{session_id}", response_model=FormSession, summary="Set field values (wizard or agent)")
def patch(session_id: str, body: FieldPatch, ctx: Context = Depends(require(Scope.prepare_applications))):
    sess = FormSession(**(store.get("form_sessions", session_id) or PAL080_SESSION.model_dump()))
    for k, v in body.values.items():
        sess.values[k] = FieldValue(value=v, confirmed=body.confirm)
    sess.updated_at = now_iso()
    store.put("form_sessions", session_id, sess.model_dump(), subject_id=ctx.subject.id)
    return sess


@router.post("/sessions/{session_id}/render", summary="Render filled official PDF (draft – never submitted)")
def render(session_id: str, ctx: Context = Depends(require(Scope.prepare_applications))):
    tpl = get_settings().knowledge_dir / "forms" / "templates" / f"{PAL080_DEF.form_id}.pdf"
    return FileResponse(tpl, media_type="application/pdf", filename="Antrag_Pflegegeld_ENTWURF.pdf")  # STUB: blank template
