"""cases — 'Mein Fall': steps + status. STUB (owner: WS-C)."""

from fastapi import APIRouter, Depends, HTTPException

from app.contracts.cases import Case, CaseCreate, StepUpdate
from app.contracts.identity import Scope
from app.core.auth import Context, require
from app.core.db import store
from app.fixtures import ANNA_CASE

router = APIRouter(prefix="/api/cases", tags=["cases"])


def _load(case_id: str) -> Case:
    data = store.get("cases", case_id)
    if data:
        return Case(**data)
    if case_id == ANNA_CASE.id:
        return ANNA_CASE
    raise HTTPException(404, "Fall nicht gefunden")


@router.get("", response_model=list[Case])
def list_cases(ctx: Context = Depends(require(Scope.manage_case))):
    return store.list("cases", subject_id=ctx.subject.id) or ([ANNA_CASE] if ctx.subject.id == "anna" else [])


@router.post("", response_model=Case, summary="Create case (optionally seeded from document tasks + benefits)")
def create(body: CaseCreate, ctx: Context = Depends(require(Scope.manage_case))):
    case = ANNA_CASE.model_copy(update={"subject_id": ctx.subject.id, "title_de": body.title_de})  # STUB
    store.put("cases", case.id, case.model_dump(), subject_id=ctx.subject.id)
    return case


@router.patch("/{case_id}/steps/{step_id}", response_model=Case)
def update_step(case_id: str, step_id: str, body: StepUpdate, ctx: Context = Depends(require(Scope.manage_case))):
    case = _load(case_id)
    for s in case.steps:
        if s.id == step_id:
            s.status = body.status
    store.put("cases", case.id, case.model_dump(), subject_id=ctx.subject.id)
    return case
