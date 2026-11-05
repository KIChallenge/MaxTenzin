"""values — lookup of veränderliche Werte (veraendW). Shared by the values router and the benefits engine."""

from __future__ import annotations

from app.contracts.common import SourceKind, SourceRef
from app.contracts.misc import Value
from app.core.knowledge import json_file

DEFAULT_YEAR = 2026


def _raw(year: int) -> list[dict]:
    return [v for v in json_file("extracted/values/veraendw.json")["values"] if v["year"] == year]


def value_source(v: dict) -> SourceRef:
    label = f"{v['legal_ref']} – veraendW Tab. {v['table']} ({v['year']}), {v['bgbl']}".strip(" ,")
    return SourceRef(kind=SourceKind.value, label=label, ref=f"veraendW#{v['table']}/{v['year']}/{v['key']}")


def to_value(v: dict) -> Value:
    return Value(key=v["key"], label_de=v["label_de"], year=v["year"], value=v["value"], unit=v["unit"],
                 legal_ref=v["legal_ref"], source=value_source(v))


def get_value(key: str, year: int = DEFAULT_YEAR) -> Value | None:
    for v in _raw(year):
        if v["key"] == key:
            return to_value(v)
    return None


def require_value(key: str, year: int = DEFAULT_YEAR) -> Value:
    """Like get_value but raises — used by the benefits engine, where a missing value is a knowledge bug."""
    val = get_value(key, year)
    if val is None:
        raise KeyError(f"veraendW value '{key}' for {year} missing")
    return val


def list_values(year: int = DEFAULT_YEAR) -> list[Value]:
    return [to_value(v) for v in _raw(year)]
