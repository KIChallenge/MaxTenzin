"""benefits — catalog + deterministic eligibility. STUB (owner: WS-B)."""

from fastapi import APIRouter, Depends, HTTPException

from app.contracts.benefits import Benefit, EligibilityRequest, EligibilityResult
from app.core.auth import Context, require
from app.fixtures import ANNA_ELIGIBILITY, PFLEGEGELD

router = APIRouter(prefix="/api/benefits", tags=["benefits"])


@router.get("", response_model=list[Benefit], summary="Benefit catalog")
def catalog(ctx: Context = Depends(require())):
    return [PFLEGEGELD]  # STUB


@router.get("/{benefit_id}", response_model=Benefit, summary="One benefit incl. legal basis and sources")
def get_benefit(benefit_id: str, ctx: Context = Depends(require())):
    if benefit_id != PFLEGEGELD.id:
        raise HTTPException(404, "Leistung nicht gefunden")
    return PFLEGEGELD


@router.post("/eligibility", response_model=list[EligibilityResult], summary="Deterministic eligibility check")
def eligibility(req: EligibilityRequest, ctx: Context = Depends(require())):
    ctx.rule_ids.extend(r for e in ANNA_ELIGIBILITY for r in e.rule_ids)
    return ANNA_ELIGIBILITY  # STUB
