"""values — veränderliche Werte (yearly amounts) from veraendW. REAL."""

from fastapi import APIRouter, Depends, HTTPException

from app.contracts.misc import Value
from app.core.auth import Context, require
from app.services.values import service

router = APIRouter(prefix="/api/values", tags=["values"])


@router.get("/{key}", response_model=Value, summary="One value for a year (default 2026)")
def get_value(key: str, year: int = 2026, ctx: Context = Depends(require())):
    val = service.get_value(key, year)
    if val is None:
        raise HTTPException(404, f"Kein Wert '{key}' für {year}")
    ctx.cite(val.source.label)
    return val


@router.get("", response_model=list[Value], summary="All mapped values for a year")
def list_values(year: int = 2026, ctx: Context = Depends(require())):
    return service.list_values(year)
