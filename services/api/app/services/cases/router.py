"""cases — 'Mein Fall': steps from documented open tasks + chosen benefits, status tracking (owner: WS-C)."""

from fastapi import APIRouter, Depends, HTTPException

from app.contracts.cases import Case, CaseCreate, CaseStep, StepStatus, StepUpdate
from app.contracts.documents import DocumentAnalysis
from app.contracts.identity import Scope
from app.core.auth import Context, require
from app.core.db import store
from app.services.cases.service import build_case

router = APIRouter(prefix="/api/cases", tags=["cases"])
COLL = "cases"


def _load(case_id: str, ctx: Context) -> Case:
    data = store.get(COLL, case_id)
    if not data or data["subject_id"] != ctx.subject.id:
        raise HTTPException(404, "Fall nicht gefunden")
    return Case(**data)


def _analysis_for(document_id: str | None) -> DocumentAnalysis | None:
    if not document_id:
        return None
    data = store.get("document_analyses", document_id)
    if data:
        return DocumentAnalysis(**data)
    from app.fixtures import ANNA_ANALYSIS  # golden fallback: demo document not analysed yet
    return ANNA_ANALYSIS if document_id == ANNA_ANALYSIS.document_id else None


@router.get("", response_model=list[Case], summary="Cases of the current subject")
def list_cases(ctx: Context = Depends(require(Scope.manage_case))):
    return store.list(COLL, subject_id=ctx.subject.id)


@router.get("/{case_id}", response_model=Case, summary="One case")
def get_case(case_id: str, ctx: Context = Depends(require(Scope.manage_case))):
    return _load(case_id, ctx)


@router.post("", response_model=Case, summary="Create case from a document's open tasks + selected benefits")
def create(body: CaseCreate, ctx: Context = Depends(require(Scope.manage_case))):
    analysis = _analysis_for(body.document_id)
    if body.document_id and analysis is None:
        raise HTTPException(404, "Dokumentanalyse nicht gefunden")
    case = build_case(ctx.subject.id, body.title_de, analysis, body.benefit_ids)
    if analysis:
        ctx.cite(f"{analysis.filename} – offene Aufgaben")
    store.put(COLL, case.id, case.model_dump(), subject_id=ctx.subject.id)
    return case


@router.patch("/{case_id}/steps/{step_id}", response_model=Case, summary="Update step status and/or link a form session")
def update_step(case_id: str, step_id: str, body: StepUpdate, ctx: Context = Depends(require(Scope.manage_case))):
    case = _load(case_id, ctx)
    step = next((s for s in case.steps if s.id == step_id), None)
    if step is None:
        raise HTTPException(404, "Schritt nicht gefunden")
    if body.status:
        step.status = body.status
    if body.form_session_id:
        step.form_session_id = body.form_session_id
        if step.status == StepStatus.open:
            step.status = StepStatus.in_progress
    store.put(COLL, case.id, case.model_dump(), subject_id=ctx.subject.id)
    return case


@router.post("/{case_id}/steps", response_model=Case, summary="Add steps (idempotent by step id) – used by other services")
def add_steps(case_id: str, steps: list[CaseStep], ctx: Context = Depends(require(Scope.manage_case))):
    case = _load(case_id, ctx)
    have = {s.id for s in case.steps}
    new = [s for s in steps if s.id not in have]
    case.steps.extend(new)
    if new:
        store.put(COLL, case.id, case.model_dump(), subject_id=ctx.subject.id)
        ctx.rule_ids.append(f"cases.steps_added:{len(new)}")
    return case
