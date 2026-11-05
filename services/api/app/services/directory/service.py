"""directory — responsible offices from knowledge/offices.yaml, filtered by topic and ranked by postcode proximity."""

from __future__ import annotations

import math
from functools import lru_cache

from app.contracts.common import SourceKind, SourceRef
from app.contracts.misc import Office
from app.core.knowledge import yaml_file
from app.services.benefits.catalog import FORM_LABELS, brochure_ref

FORM_PAGES = {"pva_pflegegeld_pal080": 8, "fsw_foerderung": 1}

# Approximate centroids of the 23 Vienna districts (lat, lon). Used ONLY for ordering results, never shown.
VIENNA_DISTRICTS = {
    1: (48.208, 16.373), 2: (48.217, 16.398), 3: (48.198, 16.394), 4: (48.192, 16.367), 5: (48.187, 16.357),
    6: (48.196, 16.349), 7: (48.203, 16.349), 8: (48.211, 16.348), 9: (48.223, 16.356), 10: (48.165, 16.381),
    11: (48.170, 16.440), 12: (48.172, 16.322), 13: (48.180, 16.260), 14: (48.207, 16.260), 15: (48.196, 16.327),
    16: (48.212, 16.310), 17: (48.230, 16.290), 18: (48.232, 16.330), 19: (48.255, 16.335), 20: (48.240, 16.375),
    21: (48.278, 16.410), 22: (48.235, 16.475), 23: (48.142, 16.290),
}


def vienna_district(zip_: str) -> int | None:
    if len(zip_) == 4 and zip_.isdigit() and zip_[0] == "1":
        d = int(zip_[1:3])
        return d if d in VIENNA_DISTRICTS else None
    return None


def _km(a: tuple[float, float], b: tuple[float, float]) -> float:
    dx = (a[1] - b[1]) * 111.32 * math.cos(math.radians((a[0] + b[0]) / 2))
    dy = (a[0] - b[0]) * 110.57
    return math.hypot(dx, dy)


def proximity(query_zip: str, office_zip: str) -> float:
    """Smaller = closer. Nationwide services (no zip) rank last but are kept."""
    if not office_zip:
        return 10_000.0
    qd, od = vienna_district(query_zip), vienna_district(office_zip)
    if qd and od:
        return _km(VIENNA_DISTRICTS[qd], VIENNA_DISTRICTS[od])
    if not (query_zip.isdigit() and office_zip.isdigit()):
        return 5_000.0
    same_region = query_zip[0] == office_zip[0]
    return (0 if same_region else 1_000) + abs(int(query_zip) - int(office_zip)) / 10


def _source(o: dict) -> SourceRef:
    if "page" in o:
        return brochure_ref(int(o["page"]))
    form = o["form"]
    page = FORM_PAGES[form]
    return SourceRef(kind=SourceKind.form, label=f"{FORM_LABELS.get(form, form)}, S. {page}", ref=f"{form}#page={page}")


@lru_cache
def offices() -> list[Office]:
    raw = yaml_file("offices.yaml") or {"offices": []}
    out = []
    for o in raw["offices"]:
        out.append(Office(id=o["id"], name=o["name"], provider=str(o["provider"]), topics=list(o["topics"]),
                          address=o["address"], zip=str(o.get("zip", "")), city=o["city"], phone=str(o.get("phone", "")),
                          email=o.get("email", ""), web=o.get("web", ""), source=_source(o)))
    return out


def search(topic: str | None = None, zip_: str | None = None, provider: str | None = None,
           limit: int | None = None) -> list[Office]:
    res = [o for o in offices()
           if (topic is None or topic.lower() in (t.lower() for t in o.topics))
           and (provider is None or o.provider.lower() == provider.lower())]
    if zip_:
        res.sort(key=lambda o: proximity(zip_, o.zip))
    return res[:limit] if limit else res
