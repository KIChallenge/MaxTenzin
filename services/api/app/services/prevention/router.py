"""prevention — e-Impfpass + Vorsorge reminders. STUB (owner: WS-D)."""

from fastapi import APIRouter, Depends

from app.contracts.identity import Scope
from app.contracts.prevention import PreventionOverview
from app.core.auth import Context, require
from app.fixtures import STEFAN_PREVENTION

router = APIRouter(prefix="/api/prevention", tags=["prevention"])


@router.get("/overview", response_model=PreventionOverview, summary="Vaccination history + due prevention items")
def overview(ctx: Context = Depends(require(Scope.view_health_prevention))):
    return STEFAN_PREVENTION.model_copy(update={"subject_id": ctx.subject.id})  # STUB


@router.post("/import/{document_id}", response_model=PreventionOverview, summary="Import vaccinations from an uploaded e-Impfpass PDF")
def import_impfpass(document_id: str, ctx: Context = Depends(require(Scope.view_health_prevention))):
    return STEFAN_PREVENTION.model_copy(update={"subject_id": ctx.subject.id})  # STUB
