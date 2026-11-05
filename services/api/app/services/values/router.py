"""values — veränderliche Werte (yearly amounts) from veraendW. REAL, minimal; WS-L may extend."""

from fastapi import APIRouter, Depends, HTTPException

from app.contracts.common import SourceKind, SourceRef
from app.contracts.misc import Value
from app.core.auth import Context, require
from app.core.knowledge import json_file

router = APIRouter(prefix="/api/values", tags=["values"])


def _to_value(v: dict) -> Value:
    return Value(key=v["key"], label_de=v["label_de"], year=v["year"], value=v["value"], unit=v["unit"], legal_ref=v["legal_ref"],
                 source=SourceRef(kind=SourceKind.value, label=f"{v['legal_ref']} – veraendW Tab. {v['table']} ({v['year']}), {v['bgbl']}".strip(" ,"),
                                  ref=f"veraendW#{v['table']}/{v['year']}/{v['key']}"))


@router.get("/{key}", response_model=Value, summary="One value for a year (default 2026)")
def get_value(key: str, year: int = 2026, ctx: Context = Depends(require())):
    for v in json_file("extracted/values/veraendw.json")["values"]:
        if v["key"] == key and v["year"] == year:
            val = _to_value(v)
            ctx.cite(val.source.label)
            return val
    raise HTTPException(404, f"Kein Wert '{key}' für {year}")


@router.get("", response_model=list[Value], summary="All mapped values for a year")
def list_values(year: int = 2026, ctx: Context = Depends(require())):
    return [_to_value(v) for v in json_file("extracted/values/veraendw.json")["values"] if v["year"] == year]
