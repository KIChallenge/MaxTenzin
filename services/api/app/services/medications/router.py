"""medications — EKO administrative lookup (never dosing/therapy advice). REAL (owner: WS-B)."""

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.contracts.misc import Medication
from app.core.auth import Context, require
from app.services.medications import service

router = APIRouter(prefix="/api/medications", tags=["medications"])


@router.get("/search", response_model=list[Medication], summary="Search EKO by product name")
def search(q: str, limit: int = Query(20, ge=1, le=100), ctx: Context = Depends(require())):
    res = service.search(q, limit)
    if res:
        ctx.cite("Erstattungskodex (EKO)")
    return res


@router.get("/{pharma_nr}", response_model=Medication, summary="One EKO pack by Pharmazentralnummer")
def get_medication(pharma_nr: str = Path(..., pattern=r"^\d{1,7}$"), ctx: Context = Depends(require())):
    med = service.get(pharma_nr)
    if med is None:
        raise HTTPException(404, "Packung nicht im Erstattungskodex gefunden")
    ctx.cite("Erstattungskodex (EKO)")
    return med
