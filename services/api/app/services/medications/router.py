"""medications — EKO administrative lookup (never dosing/therapy advice). REAL minimal; WS-B may refine wording."""

from fastapi import APIRouter, Depends

from app.contracts.common import SourceKind, SourceRef
from app.contracts.misc import Medication
from app.core.auth import Context, require
from app.core.knowledge import jsonl, value

router = APIRouter(prefix="/api/medications", tags=["medications"])

APPROVAL = {
    "RE1": "Bewilligung durch den chef-/kontrollärztlichen Dienst vor Abgabe nötig (Ihre Ärztin bzw. Ihr Arzt holt sie ein).",
    "RE2": "Keine vorherige Bewilligung; die Kasse kontrolliert nachträglich, ob die vorgesehene Verwendung dokumentiert ist.",
    "IND": "Auf Kassenkosten nur für bestimmte Anwendungsgebiete (Vermerk 'IND' auf dem Rezept).",
}


def _to_med(r: dict) -> Medication:
    fee = value("rezeptgebuehr")["value"]
    price = r["price_eur"]
    if price is not None and price <= fee:
        cost = f"Preis ({price:.2f} €) liegt unter der Rezeptgebühr ({fee:.2f} €) – Sie zahlen den Preis, ausgenommen bei Rezeptgebührenbefreiung."
    else:
        cost = f"Pro Packung fällt die Rezeptgebühr von {fee:.2f} € an (außer bei Rezeptgebührenbefreiung)."
    return Medication(
        pharma_nr=r["pharma_nr"], name=r["name"], box=r["box"], restriction=r["restriction"], pack=r["pack"], price_eur=price,
        approval_needed_de=APPROVAL.get(r["restriction"], "Frei verschreibbar (Grüner Bereich)." if r["box"] == "G" else "Gelber Bereich."),
        patient_cost_note_de=cost, rule_text=r.get("rule_text"), indication_text=r.get("indication_text"),
        source=SourceRef(kind=SourceKind.eko, label="Erstattungskodex (EKO)", ref=r["pharma_nr"]),
    )


@router.get("/search", response_model=list[Medication], summary="Search EKO by product name")
def search(q: str, limit: int = 20, ctx: Context = Depends(require())):
    ql = q.lower()
    res = [_to_med(r) for r in jsonl("extracted/eko/medications.jsonl") if ql in r["name"].lower()][:limit]
    if res:
        ctx.cite("Erstattungskodex (EKO)")
    return res
