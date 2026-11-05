"""medications — administrative EKO lookup. Never dosing, therapy or substitution advice."""

from __future__ import annotations

import re
from functools import lru_cache

from app.contracts.common import SourceKind, SourceRef
from app.contracts.misc import Medication
from app.core.knowledge import json_file, jsonl
from app.services.values import service as values

MEDS = "extracted/eko/medications.jsonl"

# Plain-language administrative wording per restriction code (codes per EKO legend, knowledge/extracted/eko/legend.json).
APPROVAL = {
    "RE1": "Bewilligung durch den chef-/kontrollärztlichen Dienst vor der Abgabe nötig – Ihre Ärztin bzw. Ihr Arzt "
           "holt sie ein.",
    "RE2": "Keine vorherige Bewilligung; die Kasse kontrolliert nachträglich, ob die vorgesehene Verwendung "
           "dokumentiert ist.",
    "IND": "Auf Kassenkosten nur für bestimmte Anwendungsgebiete (Vermerk „IND“ auf dem Rezept durch die Ärztin bzw. "
           "den Arzt).",
    "F14": "Frei verschreibbar nur bis zum vollendeten 14. Lebensjahr.",
    "F6J": "Frei verschreibbar nur bis zum vollendeten 6. Lebensjahr.",
    "F2J": "Frei verschreibbar nur bis zum vollendeten 2. Lebensjahr.",
}
BOX = {"G": "Grüner Bereich – frei verschreibbar.", "Y": "Gelber Bereich – nur mit Bewilligung bzw. nachfolgender "
                                                         "Kontrolle."}
NOTICE = " Fragen zu Wirkung, Einnahme oder Dosierung klären Sie bitte mit Ihrer Ärztin, Ihrem Arzt oder in der Apotheke."


@lru_cache
def _by_nr() -> dict[str, dict]:
    return {r["pharma_nr"]: r for r in jsonl(MEDS)}


def _eur(x: float) -> str:
    return f"{x:.2f} €".replace(".", ",")


def legend_codes() -> set[str]:
    return set(json_file("extracted/eko/legend.json")["restriction"])


def approval_text(box: str, restriction: str) -> str:
    codes = [c for c in (restriction or "").split() if c]
    parts = [APPROVAL[c] for c in codes if c in APPROVAL]
    unknown = [c for c in codes if c not in APPROVAL]
    if unknown:
        parts.append(f"Weitere Einschränkung laut Erstattungskodex: {' '.join(unknown)}.")
    if not parts:
        parts.append(BOX.get(box, "Bereich laut Erstattungskodex."))
    return " ".join(parts)


def cost_note(price: float | None, max_packs: int | None = None) -> str:
    fee = values.require_value("rezeptgebuehr").value
    if price is not None and price <= fee:
        note = (f"Der Preis ({_eur(price)}) liegt unter der Rezeptgebühr ({_eur(fee)}) – Sie zahlen den Preis, "
                "außer bei Rezeptgebührenbefreiung.")
    else:
        note = f"Pro Packung fällt die Rezeptgebühr von {_eur(fee)} an (außer bei Rezeptgebührenbefreiung)."
    note += " Beides zählt zur Rezeptgebühren-Obergrenze."
    if max_packs:
        note += f" Höchstens {max_packs} Packung(en) pro Rezept."
    return note


def to_med(r: dict) -> Medication:
    return Medication(
        pharma_nr=r["pharma_nr"], name=r["name"], box=r["box"], restriction=r["restriction"], pack=r["pack"],
        price_eur=r["price_eur"], approval_needed_de=approval_text(r["box"], r["restriction"]) + NOTICE,
        patient_cost_note_de=cost_note(r["price_eur"], r.get("max_packs")), rule_text=r.get("rule_text"),
        indication_text=r.get("indication_text"),
        source=SourceRef(kind=SourceKind.eko, label="Erstattungskodex (EKO)", ref=r["pharma_nr"]),
    )


def get(pharma_nr: str) -> Medication | None:
    r = _by_nr().get(pharma_nr.strip().zfill(7))
    return to_med(r) if r else None


def search(q: str, limit: int = 20) -> list[Medication]:
    ql = q.lower().strip()
    if not ql:
        return []
    starts = [r for r in jsonl(MEDS) if r["name"].lower().startswith(ql)]
    contains = [r for r in jsonl(MEDS) if ql in r["name"].lower() and not r["name"].lower().startswith(ql)]
    hits = starts + contains
    if not hits:
        # "Pantoprazol 20 mg" vs. 'Pantoprazol "Sandoz" 20 mg …': every token must occur (unit spacing normalised).
        tokens = [t for t in re.split(r"[\s,;]+", re.sub(r"(\d)\s*(mg|ml|g|µg|ie)\b", r"\1 \2", ql)) if t]
        hits = [r for r in jsonl(MEDS) if all(t in re.sub(r"(\d)\s*(mg|ml|g|µg|ie)\b", r"\1 \2", r["name"].lower())
                                              for t in tokens)]
    return [to_med(r) for r in hits[:limit]]
