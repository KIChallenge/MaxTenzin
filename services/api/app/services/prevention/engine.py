"""Deterministic prevention engine: person (age, sex) + documented vaccinations + as_of -> PreventionItems.

Rules and sources live in knowledge/prevention.yaml. Wording rule: never 'fehlt' — 'nicht im e-Impfpass
dokumentiert – bitte mit Ihrer Ärztin bzw. Ihrem Arzt klären'.
"""

from __future__ import annotations

from datetime import date, timedelta

from app.contracts.common import SourceKind, SourceRef
from app.contracts.identity import Person
from app.contracts.prevention import PreventionItem, PreventionStatus, VaccinationEntry
from app.core.knowledge import yaml_file

ASK_DOCTOR = "Bitte besprechen Sie das mit Ihrer Ärztin bzw. Ihrem Arzt."
NOT_DOCUMENTED = "Diese Impfung ist nicht im e-Impfpass dokumentiert – bitte mit Ihrer Ärztin bzw. Ihrem Arzt klären."


def knowledge() -> dict:
    k = yaml_file("prevention.yaml")
    if not k:
        raise RuntimeError("knowledge/prevention.yaml missing")
    return k


def source_ref(key: str) -> SourceRef:
    s = knowledge()["sources"][key]
    if s["kind"] == "external":
        return SourceRef(kind=SourceKind.external, label=s["label"], ref=s["url"])
    return SourceRef(kind=SourceKind.brochure, label=s["label"], ref=f"serviceratgeber:page:{s['page']}", quote=s["quote"])


def age_at(birth: date, on: date) -> int:
    return on.year - birth.year - ((on.month, on.day) < (birth.month, birth.day))


def de(d: date | str) -> str:
    d = date.fromisoformat(d) if isinstance(d, str) else d
    return d.strftime("%d.%m.%Y")


def _add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # 29 Feb
        return d.replace(year=d.year + years, day=28)


def _last_dose(rule: dict, vaccinations: list[VaccinationEntry]) -> date | None:
    match = set(rule.get("match") or [])
    dates = [date.fromisoformat(v.date) for v in vaccinations if match & set(v.disease.split("-"))]
    return max(dates) if dates else None


def _seasonal(rule: dict, last: date | None, as_of: date) -> tuple[PreventionStatus, date | None, str]:
    rec = rule["recommendation_de"]
    start_m, due_m = rule.get("season_start_month", 9), rule.get("due_from_month", 10)
    season_y = as_of.year if as_of.month >= start_m else as_of.year - 1
    season_start, due_start = date(season_y, start_m, 1), date(season_y, due_m, 1)
    season_end = date(season_y + 1, 4, 1)
    if last is None:
        return PreventionStatus.not_documented, None, f"{NOT_DOCUMENTED} {rec}"
    if last >= season_start:
        return (PreventionStatus.up_to_date, None,
                f"Für die aktuelle Saison ist am {de(last)} eine Impfung im e-Impfpass dokumentiert. {rec}")
    last_txt = f"Die letzte im e-Impfpass dokumentierte Impfung war am {de(last)}."
    if due_start <= as_of < season_end:
        return PreventionStatus.due, due_start, f"{last_txt} {rec} {ASK_DOCTOR}"
    nxt = due_start if as_of < due_start else date(as_of.year, due_m, 1)
    return PreventionStatus.upcoming, nxt, f"{last_txt} {rec} Die nächste Saison beginnt im Herbst."


def _interval(rule: dict, last: date | None, as_of: date, age: int) -> tuple[PreventionStatus, date | None, str]:
    rec = rule["recommendation_de"]
    if last is None:
        return PreventionStatus.not_documented, None, f"{NOT_DOCUMENTED} {rec}"
    years = rule["interval_years_60plus"] if age >= 60 and rule.get("interval_years_60plus") else rule["interval_years"]
    due = _add_years(last, years)
    last_txt = f"Die letzte im e-Impfpass dokumentierte Impfung war am {de(last)}."
    if as_of >= due:
        return PreventionStatus.due, due, f"{last_txt} {rec} {ASK_DOCTOR}"
    if due - as_of <= timedelta(days=365):
        return PreventionStatus.upcoming, due, f"{last_txt} {rec} Laut diesem Intervall wäre die nächste Auffrischung ab {de(due)} vorgesehen. {ASK_DOCTOR}"
    return PreventionStatus.up_to_date, due, f"{last_txt} {rec} Laut diesem Intervall wäre die nächste Auffrischung ab {de(due)} vorgesehen."


def _info(rule: dict, last: date | None, vaccinations: list[VaccinationEntry]) -> tuple[PreventionStatus, date | None, str]:
    rec = rule["recommendation_de"]
    if not rule.get("match"):  # programme-level info (e.g. Kinderimpfprogramm)
        if vaccinations:
            return (PreventionStatus.upcoming, None,
                    f"{rec} Welche Impfungen als Nächstes anstehen, klären Sie bitte mit Ihrer Ärztin bzw. Ihrem Arzt.")
        return PreventionStatus.not_documented, None, f"{NOT_DOCUMENTED} {rec}"
    if last is None:
        return PreventionStatus.not_documented, None, f"{NOT_DOCUMENTED} {rec}"
    return (PreventionStatus.up_to_date, None,
            (f"Im e-Impfpass ist am {de(last)} eine Impfung dokumentiert. {rec} "
             "Ob weitere Dosen vorgesehen sind, klären Sie bitte mit Ihrer Ärztin bzw. Ihrem Arzt."))


def _screening(rule: dict, age: int, birth: date) -> tuple[PreventionStatus, date | None, str]:
    rec = rule["recommendation_de"]
    hint = "Durchgeführte Untersuchungen sind hier nicht erfasst. Termine vereinbaren Sie bei Ihrer Hausärztin bzw. Ihrem Hausarzt."
    if rule["logic"] == "age_range_screening":
        lo, hi = rule["range_min"], rule["range_max"]
        if lo <= age <= hi:
            return PreventionStatus.due, None, f"{rec} {hint}"
        if age < lo:
            return PreventionStatus.upcoming, _add_years(birth, lo), f"{rule['optin_de']} {rec}"
        return PreventionStatus.not_documented, None, f"{rule['optin_de']} {ASK_DOCTOR}"
    return PreventionStatus.due, None, f"{rec} {hint}"


FAMILY_PREFIX = "Besonders relevant wegen Ihrer Familiengeschichte ({label})"


def _fold(s: str) -> str:
    s = s.strip().lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        s = s.replace(a, b)
    return " ".join(s.replace("_", " ").split())


def family_history_rules(family_history: list[str] | None) -> list[dict]:
    """Rules from knowledge/prevention.yaml#family_history matching the stated conditions (in knowledge order)."""
    if not family_history:
        return []
    stated = {_fold(x) for x in family_history if isinstance(x, str)}
    fh = knowledge().get("family_history") or {}
    return [r for r in fh.get("rules", []) if stated & {_fold(m) for m in r["match"]}]


def _apply_family_history(items: list[PreventionItem], applied: list[str], person: Person, birth: date, age: int,
                          family_history: list[str] | None) -> None:
    """Mark programme items as 'besonders relevant' (explanation cites the official programme; never a risk
    assessment) and add an info item if the programme is not shown yet because of the person's age."""
    rules = family_history_rules(family_history)
    if not rules:
        return
    note = knowledge()["family_history"]["doctor_note_de"]
    by_id = {i.id: i for i in items}
    for fr in rules:
        target = fr.get("add_if_absent")
        if target and target not in by_id:
            rule = next(r for r in knowledge()["rules"] if r["id"] == target)
            if (not rule.get("sex") or rule["sex"] == person.sex) and age < rule.get("min_age", 0):
                start = _add_years(birth, rule["min_age"])
                item = PreventionItem(
                    id=rule["id"], kind=rule["kind"], title_de=rule["title_de"], status=PreventionStatus.upcoming,
                    due_date=start.isoformat(), cost_de=rule.get("cost_de", ""),
                    # the family-history explanation below already describes the programme
                    explanation_de=f"Das Programm ist für Sie laut Alter ab {de(start)} vorgesehen.",
                    sources=[source_ref(s) for s in rule["sources"]])
                items.append(item)
                by_id[item.id] = item
        for iid in fr["items"]:
            item = by_id.get(iid)
            if item is None:
                continue
            prefix = FAMILY_PREFIX.format(label=fr["label_de"])
            if item.explanation_de.startswith("Besonders relevant"):      # several family rules hit the same item
                body = item.explanation_de.removesuffix(" " + note)
                item.explanation_de = f"{body} {fr['explanation_de']} {note}"
            else:
                item.explanation_de = f"{prefix}: {fr['explanation_de']} {item.explanation_de} {note}"
            have = {(s.label, s.quote) for s in item.sources}
            item.sources += [s for s in (source_ref(k) for k in fr["sources"]) if (s.label, s.quote) not in have]
        applied.append(f"prevention.family_history.{fr['id']}.v1")


def evaluate(person: Person, vaccinations: list[VaccinationEntry], as_of: date,
             family_history: list[str] | None = None) -> tuple[list[PreventionItem], list[str]]:
    """Returns (items, rule_ids applied). `family_history` (optional): conditions stated for the family."""
    birth = date.fromisoformat(person.birth_date)
    age = age_at(birth, as_of)
    items: list[PreventionItem] = []
    applied: list[str] = []
    for rule in knowledge()["rules"]:
        if age < rule.get("min_age", 0) or age > rule.get("max_age", 200):
            continue
        if rule.get("sex") and rule["sex"] != person.sex:
            continue
        last = _last_dose(rule, vaccinations) if rule["kind"] == "vaccination" else None
        logic = rule["logic"]
        if logic == "seasonal":
            status, due, text = _seasonal(rule, last, as_of)
        elif logic == "interval":
            status, due, text = _interval(rule, last, as_of, age)
        elif logic == "info":
            status, due, text = _info(rule, last, vaccinations)
        else:
            status, due, text = _screening(rule, age, birth)
        items.append(PreventionItem(
            id=rule["id"], kind=rule["kind"], title_de=rule["title_de"], status=status,
            due_date=due.isoformat() if due else None, last_date=last.isoformat() if last else None,
            explanation_de=text, cost_de=rule.get("cost_de", ""), sources=[source_ref(s) for s in rule["sources"]],
        ))
        applied.append(f"prevention.{rule['id']}.v1")
    _apply_family_history(items, applied, person, birth, age, family_history)
    return items, applied
