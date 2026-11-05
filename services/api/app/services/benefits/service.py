"""Deterministic eligibility engine (no LLM).

Pure functions over (subject profile, facts, explicitly documented recommendations). Every criterion carries the
SourceRef from knowledge/benefits.yaml (or the document quote), every amount comes from veraendW values or — where
the rule itself defines the amount (Satzung ÖGK § 46 Fahrtkosten) — from the cited paragraph.

Status semantics (contract EligibilityStatus):
  likely          all known criteria met (the Träger still decides)
  possible        plausible / discretionary benefit or no legal entitlement; decision by the Träger
  needs_info      facts missing -> missing_fields lists what the agent/UI should ask
  not_applicable  at least one criterion is not met

Wording is deliberately cautious: "kommt voraussichtlich in Frage", never a definitive entitlement.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.contracts.benefits import CriterionResult, EligibilityResult, EligibilityStatus
from app.contracts.common import SourceKind, SourceRef
from app.contracts.documents import Recommendation
from app.contracts.identity import Person
from app.services.benefits import catalog
from app.services.benefits.catalog import CatalogEntry
from app.services.legal import service as legal
from app.services.values import service as values

S = EligibilityStatus
RULE_VERSION = "v1"

# Rule parameters that are defined by law text (not yearly values) — each with its paragraph.
REGO_PERCENT_2026 = Decimal("0.02")          # RRZ 2008 § 13 Abs. 1a (2026: 2 %)
RGB_CHRONIC_FACTOR = Decimal("1.15")         # RRZ 2008 § 4 Abs. 1 Z 3 (115 % des Richtsatzes)
FK_FLAT, FK_FLAT_COMPANION = 7.20, 10.80     # Satzung ÖGK 2025 § 46 Abs. 5 (> 20 km bis 50 km, pro Strecke)
FK_KM, FK_KM_COMPANION = 0.13, 0.22          # Satzung ÖGK 2025 § 46 Abs. 5 (> 50 km, pro km)
FK_EXEMPT_THERAPIES = {"dialyse", "chemotherapie", "strahlentherapie"}            # § 46 Abs. 6
KT_NO_COPAY_THERAPIES = {"dialyse", "chemotherapie", "strahlentherapie", "immuntherapie"}  # § 47 Abs. 3b Z 3
KBG_MAX_DAYS_BOTH = 1063                     # Serviceratgeber 2026, S. 72
EKP_LATER_EXAMS = [(6, 22, 26), (7, 34, 38), (8, 46, 50), (9, 58, 62)]  # MuKiPassV 2002 § 9 Abs. 2–5
PG_LEVELS = [(1, 65), (2, 95), (3, 120), (4, 160)]                       # BPGG § 4 Abs. 2 (Stunden/Monat, "mehr als")

DISCLAIMER = "Unverbindliche Information – die Entscheidung trifft {provider}."


# --------------------------------------------------------------------------------------------- inputs


@dataclass
class DocRec:
    rec: Recommendation
    filename: str

    def source(self) -> SourceRef:
        return SourceRef(kind=SourceKind.document, label=f"{self.filename}, S. {self.rec.page}",
                         ref=f"page:{self.rec.page}", quote=self.rec.quote)


@dataclass
class EvalInput:
    subject: Person
    facts: dict
    recs: list[DocRec] = field(default_factory=list)
    children: list[Person] = field(default_factory=list)   # persons in the subject's Obsorge (from delegations)
    as_of: date = field(default_factory=date.today)
    living_situation: str | None = None                    # ExtractedPerson.living_situation from a document

    # ---- derived profile
    @property
    def birth(self) -> date | None:
        try:
            return date.fromisoformat(self.subject.birth_date)
        except (TypeError, ValueError):
            return None

    @property
    def age_years(self) -> int | None:
        b = self.birth
        if b is None:
            return None
        return self.as_of.year - b.year - ((self.as_of.month, self.as_of.day) < (b.month, b.day))

    @property
    def age_days(self) -> int | None:
        return (self.as_of - self.birth).days if self.birth else None

    @property
    def age_months(self) -> int | None:
        """Completed months of life."""
        b = self.birth
        if b is None:
            return None
        return (self.as_of.year - b.year) * 12 + self.as_of.month - b.month - (self.as_of.day < b.day)

    @property
    def in_vienna(self) -> bool:
        a = self.subject.address
        return a.city.strip().lower() == "wien" and len(a.zip) == 4 and a.zip.startswith("1")

    def fact(self, key: str):
        return self.facts.get(key)

    def recs_for(self, *benefit_ids: str) -> list[DocRec]:
        return [d for d in self.recs if set(benefit_ids) & set(d.rec.related_benefit_ids)]


# --------------------------------------------------------------------------------------------- helpers


def _crit(entry: CatalogEntry, cid: str, met: bool | None, explanation: str) -> CriterionResult:
    label, src = entry.criteria[cid]
    return CriterionResult(id=cid, label_de=label, met=met, explanation_de=explanation, source=src)


def _doc_crits(recs: list[DocRec]) -> list[CriterionResult]:
    return [CriterionResult(id=f"doc_{d.rec.id}", label_de="Im Dokument ausdrücklich empfohlen", met=True,
                            explanation_de=d.rec.text_de, source=d.source()) for d in recs]


def _derive(criteria: list[CriterionResult]) -> EligibilityStatus:
    mets = [c.met for c in criteria]
    if any(m is False for m in mets):
        return S.not_applicable
    if all(m is True for m in mets):
        return S.likely
    return S.needs_info


def _amount(key: str, label_de: str | None = None, **extra) -> dict:
    v = values.require_value(key)
    return {"key": key, "label_de": label_de or f"{v.label_de} ({v.year})", "value": v.value, "unit": v.unit,
            "source": v.source.model_dump(), **extra}


def _law_amount(label_de: str, value: float, unit: str, law: str, nr: str, abs_: str | None = None, **extra) -> dict:
    return {"label_de": label_de, "value": value, "unit": unit,
            "source": legal.source_ref(law, nr, abs_).model_dump(), **extra}


def _eur(x: float | Decimal) -> str:
    s = f"{float(x):,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".") + " €"


def _cent(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _bool(v) -> bool | None:
    if v is None or isinstance(v, bool):
        return v
    if isinstance(v, str):
        return {"true": True, "ja": True, "yes": True, "false": False, "nein": False, "no": False}.get(v.lower())
    return bool(v)


def _num(v) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def _result(entry: CatalogEntry, status: EligibilityStatus, criteria: list[CriterionResult], *,
            missing: list[str] | None = None, steps: list[str] | None = None, amounts: list[dict] | None = None,
            extra_rules: list[str] | None = None) -> EligibilityResult:
    steps = list(steps or [])
    steps.append(DISCLAIMER.format(provider=_provider_de(entry.benefit.provider)))
    return EligibilityResult(benefit=entry.benefit, status=status, criteria=criteria, missing_fields=missing or [],
                             next_steps_de=steps, amounts=amounts or [],
                             rule_ids=[f"{entry.benefit.id}.{RULE_VERSION}", *(extra_rules or [])])


def _provider_de(p: str) -> str:
    return {"PVA": "die Pensionsversicherungsanstalt (PVA)", "ÖGK": "die Österreichische Gesundheitskasse (ÖGK)",
            "FSW": "der Fonds Soziales Wien (FSW)"}.get(p, f"das {p}" if p.startswith("Finanzamt") else p)


def _household(inp: EvalInput) -> tuple[str | None, str]:
    """Returns (alleinstehend|paar|None, explanation of where it came from)."""
    h = inp.fact("household")
    if isinstance(h, str) and h.lower() in ("alleinstehend", "paar"):
        return h.lower(), "laut Ihrer Angabe"
    if _bool(inp.fact("lives_alone")) is True:
        return "alleinstehend", "laut Ihrer Angabe (lebt allein)"
    if inp.living_situation and "allein" in inp.living_situation.lower():
        return "alleinstehend", f"laut Dokument („{inp.living_situation}“)"
    return None, ""


# --------------------------------------------------------------------------------------------- Rezeptgebühr


@dataclass
class RgbCalc:
    status: str                     # befreit_ohne_antrag | befreit | befreit_115 | pruefen_115 | obergrenze | unknown
    limit: Decimal | None = None
    limit_115: Decimal | None = None
    rego_annual_income: Decimal | None = None
    rego_cap: Decimal | None = None
    rego_packages: int | None = None


def rezeptgebuehr_calc(net_income_monthly: float | None, household: str | None, children: int = 0,
                       chronic_expenses: bool | None = None, receives_ausgleichszulage: bool | None = None) -> RgbCalc:
    """Rezeptgebühr: befreit / Obergrenze 2 % / nicht befreit — using veraendW values + RRZ 2008 rules only."""
    if receives_ausgleichszulage:
        return RgbCalc(status="befreit_ohne_antrag")
    if net_income_monthly is None or household is None:
        return RgbCalc(status="unknown")
    base_key = "rgb_befreiungsgrenze_paar" if household == "paar" else "rgb_befreiungsgrenze_alleinstehend"
    base = Decimal(str(values.require_value(base_key).value))
    per_child = Decimal(str(values.require_value("rgb_erhoehung_pro_kind").value))
    limit = base + per_child * max(0, int(children))
    limit_115 = _cent(limit * RGB_CHRONIC_FACTOR)
    income = Decimal(str(net_income_monthly))
    floor = Decimal(str(values.require_value("az_richtsatz_alleinstehend").value))
    annual = max(income, floor) * 12                                  # RRZ § 14 (ohne Sonderzahlungen), § 16 Abs. 4
    cap = _cent(annual * REGO_PERCENT_2026)
    fee = Decimal(str(values.require_value("rezeptgebuehr").value))
    packages = math.ceil(cap / fee)
    calc = RgbCalc(status="obergrenze", limit=limit, limit_115=limit_115, rego_annual_income=annual,
                   rego_cap=cap, rego_packages=packages)
    if income <= limit:
        calc.status = "befreit"
    elif income <= limit_115:
        calc.status = "befreit_115" if chronic_expenses else ("pruefen_115" if chronic_expenses is None else "obergrenze")
    return calc


def _rgb_inputs(inp: EvalInput) -> tuple[float | None, str | None, str, int, bool | None, bool | None]:
    household, hh_src = _household(inp)
    children = int(_num(inp.fact("children_count")) or 0)
    return (_num(inp.fact("net_income_monthly")), household, hh_src, children,
            _bool(inp.fact("chronic_illness_expenses")), _bool(inp.fact("receives_ausgleichszulage")))


# --------------------------------------------------------------------------------------------- evaluators


def eval_pflegegeld(e: CatalogEntry, inp: EvalInput) -> EligibilityResult:
    recs = inp.recs_for("pflegegeld")
    months, hours = _num(inp.fact("care_need_months")), _num(inp.fact("care_hours_estimate"))
    missing: list[str] = []
    if months is None:
        missing.append("care_need_months")
        expl = ("Im Dokument wird empfohlen, den Pflegegeldanspruch zu prüfen. Ob der Pflegebedarf voraussichtlich "
                "mindestens sechs Monate andauert, stellt die PVA fest." if recs else
                "Bitte angeben, ob der Unterstützungsbedarf voraussichtlich mindestens sechs Monate dauert.")
        c6 = _crit(e, "pg_6m", None, expl)
    else:
        c6 = _crit(e, "pg_6m", months >= 6, f"Angegebene voraussichtliche Dauer: {months:g} Monate.")
    level = None
    if hours is None:
        missing.append("care_hours_estimate")
        ch = _crit(e, "pg_hours", None, "Der Pflegebedarf in Stunden wird bei einem Hausbesuch durch die PVA "
                                        "begutachtet. Eine eigene Schätzung hilft bei der Vorbereitung.")
    else:
        level = max((lv for lv, h in PG_LEVELS if hours > h), default=None)
        if level is None:
            ch = _crit(e, "pg_hours", False, f"Geschätzt {hours:g} Stunden/Monat – für Stufe 1 sind mehr als 65 "
                                             "Stunden nötig. Die Begutachtung durch die PVA kann davon abweichen.")
        else:
            more = " Stufe 5–7 setzen über 180 Stunden weitere Voraussetzungen voraus." if hours > 180 else ""
            ch = _crit(e, "pg_hours", True, f"Geschätzt {hours:g} Stunden/Monat – das entspräche voraussichtlich "
                                            f"Stufe {level}. Die Einstufung erfolgt durch die PVA.{more}")
    country = inp.subject.address.country
    cres = _crit(e, "pg_residence", country == "Österreich", f"Wohnadresse laut Stammdaten in {country}.")
    criteria = [*_doc_crits(recs), c6, ch, cres]
    status = _derive(criteria)
    amounts = [_amount(f"pflegegeld_stufe_{n}", estimated=(n == level)) for n in range(1, 8)]
    steps = ["Antrag auf Pflegegeld (PAL 080) mit dem Formular-Assistenten vorbereiten, prüfen und unterschreiben.",
             "Aktuelle Befunde (z. B. Entlassungsbrief) in Kopie beilegen.",
             "Antrag an die zuständige PVA-Landesstelle senden (siehe Zuständigkeiten).",
             "Die PVA vereinbart einen Hausbesuch zur Begutachtung des Pflegebedarfs.",
             "Im Antrag (Punkt 9) kann zusätzlich eine kostenlose Pflegeberatung zu Hause gewünscht werden."]
    if status == S.not_applicable:
        steps = [("Nach den bekannten Angaben sind die Voraussetzungen derzeit voraussichtlich nicht erfüllt. "
                 "Bei Verschlechterung kann jederzeit ein Antrag gestellt werden.")]
    return _result(e, status, criteria, missing=missing, steps=steps, amounts=amounts)


def eval_pflegeberatung(e: CatalogEntry, inp: EvalInput) -> EligibilityResult:
    direct = inp.recs_for("pflegeberatung")
    trigger = inp.recs_for("pflegegeld", "pflegeberatung", "fsw_mobile_pflege")
    gets, applies = _bool(inp.fact("receives_pflegegeld")), _bool(inp.fact("pflegegeld_applied"))
    if gets or applies:
        c = _crit(e, "pb_care", True, "Pflegegeld wird bezogen bzw. beantragt – die Beratung kann im Antrag "
                                      "(Punkt 9) oder bei der PVA gewünscht werden.")
    else:
        c = _crit(e, "pb_care", None, "Die kostenlose Pflegeberatung kann beim Pflegegeldantrag (PAL 080, Punkt 9) "
                                      "angekreuzt werden.")
    criteria = [*_doc_crits(direct), c]
    if c.met:
        status = S.likely
    elif trigger:
        status = S.possible
    else:
        status = S.needs_info
    steps = [("Im Pflegegeldantrag (PAL 080) bei Punkt 9 „Ja“ ankreuzen – die Beratung durch eine diplomierte "
             "Pflegefachkraft ist kostenlos."),
             ("Wird der Antrag von einer anderen Person gestellt, vorher die Zustimmung der pflegebedürftigen Person "
             "zur Weitergabe der Kontaktdaten einholen.")]
    missing = [] if c.met or trigger else ["pflegegeld_applied"]
    return _result(e, status, criteria, missing=missing, steps=steps,
                   amounts=[{"label_de": "Pflegeberatung zu Hause", "value": 0.0, "unit": "EUR",
                             "source": e.benefit.sources[0].model_dump()}])


def eval_fsw(e: CatalogEntry, inp: EvalInput) -> EligibilityResult:
    recs = inp.recs_for("fsw_mobile_pflege")
    cv = _crit(e, "fsw_vienna", inp.in_vienna,
               f"Wohnadresse laut Stammdaten: {inp.subject.address.zip} {inp.subject.address.city}."
               + ("" if inp.in_vienna else " Der FSW ist nur für Menschen mit Hauptwohnsitz in Wien zuständig."))
    need = _bool(inp.fact("care_need_at_home"))
    missing: list[str] = []
    if need is None and recs:
        cn = _crit(e, "fsw_need", True, "Im Dokument wird Unterstützung bei der Pflege zu Hause empfohlen "
                                        "(siehe Zitat). Den genauen Bedarf erhebt der FSW.")
    elif need is None:
        missing.append("care_need_at_home")
        cn = _crit(e, "fsw_need", None, "Bitte angeben, ob Unterstützung bei Pflege oder Betreuung zu Hause nötig ist.")
    else:
        cn = _crit(e, "fsw_need", need, "Laut Ihrer Angabe." + ("" if need else " Ohne Unterstützungsbedarf "
                                                                                 "kommt die Leistung nicht in Frage."))
    criteria = [*_doc_crits(recs), cv, cn]
    status = _derive(criteria)
    steps = [("Beim FSW-Kund:innenservice (Tel. 01 24 5 24) beraten lassen; der FSW erhebt den Pflege- und "
             "Betreuungsbedarf."),
             "Antrag auf Förderung von Leistungen (FSW) vorbereiten; Einkommensnachweise und Wohnkosten beilegen.",
             "Für bestimmte Leistungen ist ein Kostenbeitrag zu zahlen; er hängt u. a. vom Einkommen und Pflegegeld ab."]
    return _result(e, status, criteria, missing=missing, steps=steps)


def eval_hauskrankenpflege(e: CatalogEntry, inp: EvalInput) -> EligibilityResult:
    order = _bool(inp.fact("home_nursing_ordered"))
    co = _crit(e, "hkp_order", order,
               "Medizinische Hauskrankenpflege ist nur auf ärztliche Anordnung möglich; Grundpflege und "
               "Haushaltshilfe sind nicht umfasst." if order is None else
               ("Laut Ihrer Angabe liegt eine ärztliche Anordnung vor." if order else
                "Laut Ihrer Angabe liegt keine ärztliche Anordnung vor."))
    ci = _crit(e, "hkp_insured", bool(inp.subject.insurer), f"Krankenversicherung laut Stammdaten: {inp.subject.insurer}.")
    criteria = [co, ci]
    status = _derive(criteria)
    steps = [("Mit der behandelnden Ärztin bzw. dem behandelnden Arzt klären, ob medizinische Hauskrankenpflege "
             "angeordnet wird."),
             ("Sie wird grundsätzlich für bis zu vier Wochen gewährt; eine Verlängerung braucht eine Bewilligung des "
             "Medizinischen Dienstes.")]
    return _result(e, status, criteria, missing=[] if order is not None else ["home_nursing_ordered"], steps=steps)


def eval_reha_onko(e: CatalogEntry, inp: EvalInput) -> EligibilityResult:
    recs = inp.recs_for("reha_onko")
    applied = _bool(inp.fact("reha_application_with_medical_statement"))
    ca = _crit(e, "reha_application", applied,
               "Der Antrag braucht eine medizinische Begründung; die ärztliche Stellungnahme füllt Ihre Ärztin bzw. "
               "Ihr Arzt aus." if applied is None else "Laut Ihrer Angabe.")
    ci = _crit(e, "reha_insured", bool(inp.subject.insurer), f"Versichert laut Stammdaten: {inp.subject.insurer}.")
    criteria = [*_doc_crits(recs), ca, ci]
    if any(c.met is False for c in criteria):
        status = S.not_applicable
    elif recs or applied:
        status = S.possible          # Ermessensleistung ("nach pflichtgemäßem Ermessen") -> never "likely"
    else:
        status = S.needs_info
    amounts = []
    gross = _num(inp.fact("gross_income_monthly"))
    if _bool(inp.fact("receives_ausgleichszulage")):
        amounts.append(_amount("reha_zuzahlung_frei_bis", "Keine Zuzahlung (Ausgleichszulage)", per_day=0.0))
    elif gross is not None:
        if gross <= values.require_value("reha_zuzahlung_frei_bis").value:
            amounts.append(_amount("reha_zuzahlung_frei_bis", "Keine Zuzahlung bis zu diesem Bruttoeinkommen (2026)"))
        elif gross <= values.require_value("reha_stufe1_bis").value:
            amounts.append(_amount("reha_stufe1_pro_tag", "Voraussichtliche Zuzahlung pro Tag (2026)"))
        elif gross <= values.require_value("reha_stufe2_bis").value:
            amounts.append(_amount("reha_stufe2_pro_tag", "Voraussichtliche Zuzahlung pro Tag (2026)"))
        else:
            amounts.append(_amount("reha_stufe3_pro_tag", "Voraussichtliche Zuzahlung pro Tag (2026)"))
    else:
        amounts = [_amount(k) for k in ("reha_zuzahlung_frei_bis", "reha_stufe1_pro_tag", "reha_stufe2_pro_tag",
                                        "reha_stufe3_pro_tag")]
    steps = ["Antrag auf Rehabilitations-, Kur- bzw. Erholungsaufenthalt vorbereiten (Ihre Angaben).",
             "Die ärztliche Stellungnahme (Seite 2) füllt die behandelnde Ärztin bzw. der behandelnde Arzt aus.",
             "Die Zuzahlung ist für höchstens 28 Tage im Kalenderjahr zu leisten und hängt vom Bruttoeinkommen ab."]
    missing = [] if applied is not None else ["reha_application_with_medical_statement"]
    if gross is None and not _bool(inp.fact("receives_ausgleichszulage")):
        missing.append("gross_income_monthly")
    return _result(e, status, criteria, missing=missing, steps=steps, amounts=amounts)


def eval_krankentransport(e: CatalogEntry, inp: EvalInput) -> EligibilityResult:
    recs = inp.recs_for("krankentransport")
    walk = _bool(inp.fact("walking_unable_confirmed"))
    cw = _crit(e, "kt_walking", walk,
               "Die Kosten werden nur übernommen, wenn eine ärztliche Transportanweisung die Gehunfähigkeit bestätigt "
               "(auch nicht in Begleitung oder mit Gehhilfe). Bei Immundefizienz aufgrund einer Tumorbehandlung kann "
               "ein Transport grundsätzlich verordnet werden – das entscheidet die Ärztin bzw. der Arzt."
               if walk is None else ("Laut Ihrer Angabe liegt eine ärztliche Transportanweisung vor." if walk else
                                     "Laut Ihrer Angabe liegt keine ärztliche Transportanweisung vor. Das Fehlen "
                                     "einer Begleitperson oder eines Verkehrsmittels begründet keine Übernahme."))
    therapy = str(inp.fact("treatment_type") or "").lower()
    exempt_rgb = _bool(inp.fact("rgb_exempt"))
    young = (inp.age_years or 99) < 15
    no_copay = therapy in KT_NO_COPAY_THERAPIES or exempt_rgb or young
    why = ("Strahlen-, Chemo-, Immuntherapie oder Dialyse" if therapy in KT_NO_COPAY_THERAPIES else
           "Rezeptgebührenbefreiung" if exempt_rgb else "Kind unter 15 Jahren" if young else "")
    criteria = [*_doc_crits(recs), cw]
    amounts = []
    if no_copay:
        criteria.append(_crit(e, "kt_copay", True, f"Kein Kostenanteil pro Fahrtstrecke ({why})."))
        amounts.append(_law_amount(f"Kostenanteil pro Fahrtstrecke ({why})", 0.0, "EUR", "Satzung_OEGK_2025", "47",
                                   "3b"))
    else:
        fee = values.require_value("rezeptgebuehr")
        amounts.append(_amount("rezeptgebuehr", "Kostenanteil Krankenbeförderung (Taxi/Fahrtendienst) pro Strecke"))
        amounts.append({"key": "rezeptgebuehr_x2", "label_de": "Kostenanteil Krankentransport mit Sanitäter:in pro "
                        "Strecke (doppelte Rezeptgebühr)", "value": round(fee.value * 2, 2), "unit": "EUR",
                        "source": fee.source.model_dump()})
    status = _derive([cw])
    steps = [("Mit der behandelnden Ärztin bzw. dem behandelnden Arzt klären, ob eine Transportanweisung "
             "(Gehunfähigkeit) ausgestellt wird."),
             "Die Art des Transports (Krankenbeförderung oder Krankentransport) wird ärztlich bescheinigt.",
             "Der Kostenanteil fällt für höchstens 28 Fahrten pro Kalenderjahr an und wird nachträglich vorgeschrieben."]
    return _result(e, status, criteria, missing=[] if walk is not None else ["walking_unable_confirmed"],
                   steps=steps, amounts=amounts)


def eval_fahrtkosten(e: CatalogEntry, inp: EvalInput) -> EligibilityResult:
    recs = inp.recs_for("fahrtkostenzuschuss")
    therapy = str(inp.fact("treatment_type") or "").lower()
    exempt = _bool(inp.fact("rgb_exempt"))
    missing: list[str] = []
    if therapy in FK_EXEMPT_THERAPIES:
        cg = _crit(e, "fk_entitled_group", True, f"Bei Fahrten zur {therapy.capitalize()} wird der Zuschuss auch "
                                                 "ohne Rezeptgebührenbefreiung gewährt.")
    elif exempt is not None:
        cg = _crit(e, "fk_entitled_group", exempt, "Laut Ihrer Angabe " + ("besteht" if exempt else "besteht keine")
                   + " Rezeptgebührenbefreiung (die Obergrenze allein reicht nicht).")
    else:
        missing += ["rgb_exempt", "treatment_type"]
        cg = _crit(e, "fk_entitled_group", None, "Der Zuschuss gilt grundsätzlich nur bei Rezeptgebührenbefreiung. "
                                                 "Ausnahme: Fahrten zu Dialyse, Chemo- oder Strahlentherapie.")
    km = _num(inp.fact("distance_km"))
    outside = _bool(inp.fact("treatment_outside_home_town"))
    if km is not None:
        ok = km > 20 and outside is not False
        cd = _crit(e, "fk_distance", ok, f"Angegebene Entfernung: {km:g} km."
                   + ("" if ok else " Ersetzt werden nur Fahrten außerhalb des Ortsgebiets über 20 km."))
    elif outside is False:
        cd = _crit(e, "fk_distance", False, "Die Behandlungsstelle liegt laut Ihrer Angabe im Wohnort. Fahrten "
                                            "innerhalb des Ortsgebiets werden nicht ersetzt.")
    else:
        missing.append("distance_km")
        hint = (" Bei Behandlungen innerhalb Wiens liegt die Fahrt im Ortsgebiet – dann kommt der Zuschuss "
                "voraussichtlich nicht in Frage." if inp.in_vienna else "")
        cd = _crit(e, "fk_distance", None, "Ersetzt werden nur Fahrten außerhalb des Ortsgebiets, wenn die "
                                           "nächstgelegene geeignete Behandlungsstelle mehr als 20 km entfernt ist."
                   + hint)
    criteria = [*_doc_crits(recs), cg, cd]
    status = _derive([cg, cd])
    companion = _bool(inp.fact("companion_needed")) or (inp.age_years or 99) < 15
    if km is not None and km > 50:
        rate = FK_KM_COMPANION if companion else FK_KM
        amounts = [_law_amount("Zuschuss pro Strecke (km × Kilometersatz)", round(km * rate, 2), "EUR",
                               "Satzung_OEGK_2025", "46", "5", per_km=rate)]
    elif km is not None and km > 20:
        amounts = [_law_amount("Pauschaler Zuschuss pro Strecke (über 20 bis 50 km)",
                               FK_FLAT_COMPANION if companion else FK_FLAT, "EUR", "Satzung_OEGK_2025", "46", "5")]
    else:
        amounts = [_law_amount("Pauschale pro Strecke über 20 bis 50 km", FK_FLAT, "EUR", "Satzung_OEGK_2025", "46", "5"),
                   _law_amount("Pauschale pro Strecke über 20 bis 50 km mit Begleitperson", FK_FLAT_COMPANION, "EUR",
                               "Satzung_OEGK_2025", "46", "5"),
                   _law_amount("Kilometersatz über 50 km", FK_KM, "EUR/km", "Satzung_OEGK_2025", "46", "5"),
                   _law_amount("Kilometersatz über 50 km mit Begleitperson", FK_KM_COMPANION, "EUR/km",
                               "Satzung_OEGK_2025", "46", "5")]
    steps = ["Antrag auf Zuschuss zu Fahrtkosten vorbereiten; die Behandlungsstelle bestätigt jede Fahrt mit Stempel.",
             "Belege über die tatsächlichen Kosten in Kopie beilegen – ersetzt werden höchstens diese Kosten.",
             "Wurde ein Krankentransport durchgeführt, gibt es für dieselbe Fahrt keinen Fahrtkostenzuschuss."]
    if status == S.not_applicable:
        steps = ["Nach den bekannten Angaben kommt der Fahrtkostenzuschuss voraussichtlich nicht in Frage.",
                 "Wenn Gehunfähigkeit ärztlich bestätigt wird, kann stattdessen ein Krankentransport in Frage kommen."]
    return _result(e, status, criteria, missing=missing, steps=steps, amounts=amounts)


def eval_rgb_befreiung(e: CatalogEntry, inp: EvalInput) -> EligibilityResult:
    recs = inp.recs_for("rezeptgebuehrenbefreiung")
    income, household, hh_src, children, chronic, az = _rgb_inputs(inp)
    calc = rezeptgebuehr_calc(income, household, children, chronic, az)
    missing: list[str] = []
    criteria = _doc_crits(recs)
    if calc.status == "befreit_ohne_antrag":
        criteria.append(_crit(e, "rgb_auto", True, "Laut Ihrer Angabe wird eine Ausgleichszulage bezogen – die "
                                                   "Befreiung gilt ohne Antrag."))
        status = S.likely
    else:
        criteria.append(_crit(e, "rgb_auto", None if az is None else False,
                              "Bei Bezug einer Ausgleichszulage gilt die Befreiung ohne Antrag."))
        if income is None:
            missing.append("net_income_monthly")
        if household is None:
            missing.append("household")
        if calc.status == "unknown":
            criteria.append(_crit(e, "rgb_income", None, "Für die Prüfung brauchen wir das monatliche Nettoeinkommen "
                                                         "und ob Sie allein oder als Paar leben."))
            status = S.needs_info
        else:
            kids = f" + {children} Kind(er)" if children else ""
            hh = "alleinstehend" if household == "alleinstehend" else "Ehepaar/Lebensgemeinschaft"
            base = f"Richtsatz {hh}{kids} ({hh_src}): {_eur(calc.limit)}; Ihr Nettoeinkommen: {_eur(income)}."
            if calc.status == "befreit":
                criteria.append(_crit(e, "rgb_income", True, base + " Eine Befreiung auf Antrag kommt voraussichtlich "
                                                                    "in Frage."))
                status = S.likely
            elif calc.status == "befreit_115":
                criteria.append(_crit(e, "rgb_income", True, base + f" Wegen nachgewiesener krankheitsbedingter "
                                      f"Mehrausgaben gilt die Grenze von 115 % ({_eur(calc.limit_115)})."))
                status = S.likely
            elif calc.status == "pruefen_115":
                criteria.append(_crit(e, "rgb_income", None, base + f" Bei nachgewiesenen krankheitsbedingten "
                                      f"Mehrausgaben gilt die Grenze von 115 % ({_eur(calc.limit_115)})."))
                missing.append("chronic_illness_expenses")
                status = S.needs_info
            else:
                criteria.append(_crit(e, "rgb_income", False, base + " Das Einkommen liegt über der Grenze – es gilt "
                                      "aber die Rezeptgebühren-Obergrenze (2 % des Jahresnettoeinkommens)."))
                status = S.not_applicable
    amounts = [_amount("rezeptgebuehr", "Rezeptgebühr pro Packung (2026)")]
    if calc.limit is not None:
        key = "rgb_befreiungsgrenze_paar" if household == "paar" else "rgb_befreiungsgrenze_alleinstehend"
        src = values.require_value(key).source.model_dump()
        amounts.append({"label_de": "Ihre Befreiungsgrenze (netto/Monat)", "value": float(calc.limit), "unit": "EUR",
                        "source": src})
        amounts.append({"label_de": "Grenze bei krankheitsbedingten Mehrausgaben (115 %)",
                        "value": float(calc.limit_115), "unit": "EUR", "source": src,
                        "rule_source": legal.source_ref("RRZ_2008", "4", "1").model_dump()})
    else:
        amounts += [_amount("rgb_befreiungsgrenze_alleinstehend"), _amount("rgb_befreiungsgrenze_paar"),
                    _amount("rgb_erhoehung_pro_kind")]
    steps = ["Antrag auf Rezeptgebührenbefreiung bei der ÖGK stellen (Kundenservice oder online).",
             ("Einkommensnachweise aller im gemeinsamen Haushalt lebenden Personen beilegen (Einkommen von "
             "Ehepartner:in/Lebensgefährt:in zur Gänze, sonstiger Personen zu 12,5 %)."),
             ("Mit Rezeptgebührenbefreiung entfällt u. a. der Kostenanteil bei Krankentransporten; ein "
             "Fahrtkostenzuschuss kann in Frage kommen.")]
    return _result(e, status, criteria, missing=missing, steps=steps, amounts=amounts)


def eval_rego(e: CatalogEntry, inp: EvalInput) -> EligibilityResult:
    income = _num(inp.fact("net_income_monthly"))
    calc = rezeptgebuehr_calc(income, "alleinstehend")   # REGO depends on own income only
    if income is None:
        c = _crit(e, "rego_income", None, "Die Obergrenze beträgt 2026 2 % des Jahresnettoeinkommens (ohne "
                                          "Sonderzahlungen). Für die Berechnung brauchen wir das Nettoeinkommen.")
        criteria, status, missing, amounts = [c], S.needs_info, ["net_income_monthly"], []
    else:
        floor_note = (" (Mindestgrenze: 12 × Ausgleichszulagen-Richtsatz)"
                      if Decimal(str(income)) < calc.rego_annual_income / 12 else "")
        c = _crit(e, "rego_income", True,
                  f"Jahresnettoeinkommen{floor_note}: {_eur(calc.rego_annual_income)}; 2 % davon: "
                  f"{_eur(calc.rego_cap)}. Danach sind Sie für den Rest des Kalenderjahres automatisch befreit "
                  f"(das sind rund {calc.rego_packages} Packungen zu je "
                  f"{_eur(values.require_value('rezeptgebuehr').value)}).")
        criteria, status, missing = [c], S.likely, []
        amounts = [_law_amount("Rezeptgebühren-Obergrenze 2026 (pro Jahr)", float(calc.rego_cap), "EUR",
                               "RRZ_2008", "13", "1a", packages=calc.rego_packages)]
    amounts.append(_amount("rezeptgebuehr", "Rezeptgebühr pro Packung (2026)"))
    steps = ["Die Obergrenze wird von der ÖGK automatisch berücksichtigt – ein Antrag ist nicht nötig.",
             "Die Befreiung wegen Obergrenze endet am 31.12.; ab 1.1. zählt das neue Jahr.",
             "Rezeptgebühren, die Sie für mitversicherte Angehörige bezahlen, werden mit eingerechnet."]
    return _result(e, status, criteria, missing=missing, steps=steps, amounts=amounts)


def eval_ufonds(e: CatalogEntry, inp: EvalInput) -> EligibilityResult:
    costs = _num(inp.fact("costs_eur"))
    if costs is None:
        cc = _crit(e, "uf_costs", None, "Bitte angeben, welche krankheitsbedingten Kosten (mindestens 40 €) entstehen.")
    else:
        cc = _crit(e, "uf_costs", costs >= 40, f"Angegebene Kosten: {_eur(costs)}.")
    cs = _crit(e, "uf_situation", None, "Die ÖGK berücksichtigt Familien-, Einkommens- und Vermögensverhältnisse "
                                        "aller im Haushalt lebenden Personen. Es besteht kein Rechtsanspruch.")
    criteria = [cc, cs]
    if cc.met is False:
        status = S.not_applicable
    elif cc.met:
        status = S.possible
    else:
        status = S.needs_info
    steps = ["Schriftlichen Antrag an die ÖGK stellen.",
             ("Einkommensnachweise aller im Haushalt lebenden Personen sowie Rechnungen bzw. Kostenvoranschläge "
             "beilegen.")]
    return _result(e, status, criteria, missing=[] if costs is not None else ["costs_eur"], steps=steps)


def eval_vorsorge(e: CatalogEntry, inp: EvalInput) -> EligibilityResult:
    age = inp.age_years
    if age is None:
        ca = _crit(e, "vu_age", None, "Geburtsdatum unbekannt.")
    else:
        colo = " Ab 45 Jahren wird alle zehn Jahre zusätzlich eine Koloskopie angeboten." if age >= 45 else ""
        ca = _crit(e, "vu_age", age >= 18, f"Alter laut Stammdaten: {age} Jahre." + (colo if age >= 18 else
                   " Die Vorsorgeuntersuchung gibt es ab 18 Jahren; für Kinder gibt es die "
                   "Eltern-Kind-Pass-Untersuchungen."))
    ci = _crit(e, "vu_insured", bool(inp.subject.insurer), f"Versichert laut Stammdaten: {inp.subject.insurer}.")
    criteria = [ca, ci]
    status = _derive(criteria)
    steps = ["Termin bei der Hausärztin bzw. beim Hausarzt (oder einer Einrichtung mit VU-Vertrag) vereinbaren.",
             "e-card mitnehmen; die Untersuchung ist einmal jährlich kostenlos."]
    return _result(e, status, criteria, missing=[] if age is not None else ["birth_date"], steps=steps,
                   amounts=[{"label_de": "Vorsorgeuntersuchung", "value": 0.0, "unit": "EUR",
                             "source": catalog.brochure_ref(23).model_dump()}])


def _child_target(inp: EvalInput) -> tuple[Person | None, EvalInput | None]:
    """Family benefits: the subject is the child (parent acts via Obsorge) or an adult with children in Obsorge."""
    if inp.age_years is not None and inp.age_years < 18:
        return inp.subject, inp
    if inp.children:
        c = max(inp.children, key=lambda p: p.birth_date)   # youngest child (most family benefits are age-bound)
        return c, EvalInput(subject=c, facts=inp.facts, as_of=inp.as_of)
    return None, None


def _no_child(e: CatalogEntry, cid: str) -> EligibilityResult:
    crit = _crit(e, cid, False, "Für diese Person ist kein minderjähriges Kind hinterlegt. Wenn Kinder im Haushalt "
                                "leben, bitte als Vertretung (Obsorge) hinzufügen.")
    return _result(e, S.not_applicable, [crit])


def eval_familienbeihilfe(e: CatalogEntry, inp: EvalInput) -> EligibilityResult:
    child, cinp = _child_target(inp)
    if child is None or cinp is None:
        return _no_child(e, "fb_minor")
    cm = _crit(e, "fb_minor", (cinp.age_years or 0) < 18,
               f"{child.first_name} ist laut Stammdaten {cinp.age_years} Jahre alt.")
    cr = _crit(e, "fb_residence", child.address.country == "Österreich",
               f"Wohnadresse laut Stammdaten in {child.address.country}.")
    criteria = [cm, cr]
    received = _bool(inp.fact("familienbeihilfe_received"))
    status = S.likely if received else (S.not_applicable if _derive(criteria) == S.not_applicable else S.possible)
    steps = [("Falls noch nicht beantragt: Antrag auf Familienbeihilfe beim Finanzamt Österreich stellen "
             "(der Elternteil stellt den Antrag)."),
             "Die Familienbeihilfe ist Voraussetzung für das Kinderbetreuungsgeld."]
    return _result(e, status, criteria, steps=steps,
                   missing=[] if received is not None else ["familienbeihilfe_received"])


def eval_kbg(e: CatalogEntry, inp: EvalInput) -> EligibilityResult:
    child, cinp = _child_target(inp)
    if child is None or cinp is None:
        return _no_child(e, "kbg_age")
    days = cinp.age_days or 0
    ca = _crit(e, "kbg_age", days <= KBG_MAX_DAYS_BOTH,
               f"{child.first_name} ist {days} Tage alt. Die längste Variante (beide Elternteile) reicht bis "
               f"{KBG_MAX_DAYS_BOTH} Tage ab Geburt; rückwirkend werden höchstens 182 Tage ausbezahlt.")
    fb = _bool(inp.fact("familienbeihilfe_received"))
    cf = _crit(e, "kbg_fb", fb, "Laut Ihrer Angabe." if fb is not None else
               "Kinderbetreuungsgeld setzt den Bezug der Familienbeihilfe voraus.")
    hh = _bool(inp.fact("shared_household_with_child"))
    ch = _crit(e, "kbg_household", hh, "Laut Ihrer Angabe." if hh is not None else
               "Elternteil und Kind müssen im gemeinsamen Haushalt mit identer Hauptwohnsitzmeldung leben.")
    criteria = [ca, cf, ch]
    status = S.not_applicable if any(c.met is False for c in criteria) else S.possible
    missing = [k for k, v in (("familienbeihilfe_received", fb), ("shared_household_with_child", hh)) if v is None]
    steps = ["Antrag beim zuständigen Krankenversicherungsträger (ÖGK) stellen; Bezugsvariante sorgfältig wählen.",
             "Nachweise der Eltern-Kind-Pass-Untersuchungen bereithalten – sonst wird das Kinderbetreuungsgeld gekürzt.",
             "Die Zuverdienstgrenze pro Kalenderjahr beachten."]
    amounts = [_amount("kbg_taeglich", "Kinderbetreuungsgeld pro Tag (Konto, kürzeste Variante, 2026)")]
    return _result(e, status, criteria, missing=missing, steps=steps, amounts=amounts)


def eval_ekp(e: CatalogEntry, inp: EvalInput) -> EligibilityResult:
    child, cinp = _child_target(inp)
    if child is None or cinp is None:
        return _no_child(e, "ekp_age")
    months = cinp.age_months or 0
    nxt = next(((n, a, b) for n, a, b in EKP_LATER_EXAMS if months + 1 <= b), None)
    if months + 1 <= 14:
        hint = " Die Untersuchungen bis zum 14. Lebensmonat sind Voraussetzung für das volle Kinderbetreuungsgeld."
    elif nxt:
        n, a, b = nxt
        when = "jetzt" if a <= months + 1 <= b else f"ab dem {a}. Lebensmonat"
        hint = f" Laut Untersuchungsprogramm ist die {n}. Untersuchung im {a}.–{b}. Lebensmonat vorgesehen ({when})."
    else:
        hint = ""
    ca = _crit(e, "ekp_age", months < 62, f"{child.first_name} ist im {months + 1}. Lebensmonat.{hint}")
    status = S.possible if ca.met else S.not_applicable
    steps = [("Termin für die nächste Eltern-Kind-Pass-Untersuchung bei der Kinderärztin bzw. beim Kinderarzt "
             "vereinbaren."), "Untersuchungsbestätigungen aufbewahren."]
    return _result(e, status, [ca], steps=steps,
                   amounts=[{"label_de": "Eltern-Kind-Pass-Untersuchung", "value": 0.0, "unit": "EUR",
                             "source": catalog.brochure_ref(74).model_dump()}])


EVALUATORS: dict[str, Callable[[CatalogEntry, EvalInput], EligibilityResult]] = {
    "pflegegeld": eval_pflegegeld,
    "pflegeberatung": eval_pflegeberatung,
    "fsw_mobile_pflege": eval_fsw,
    "hauskrankenpflege": eval_hauskrankenpflege,
    "reha_onko": eval_reha_onko,
    "krankentransport": eval_krankentransport,
    "fahrtkostenzuschuss": eval_fahrtkosten,
    "rezeptgebuehrenbefreiung": eval_rgb_befreiung,
    "rezeptgebuehrenobergrenze": eval_rego,
    "unterstuetzungsfonds": eval_ufonds,
    "vorsorgeuntersuchung": eval_vorsorge,
    "familienbeihilfe": eval_familienbeihilfe,
    "kinderbetreuungsgeld": eval_kbg,
    "eltern_kind_pass": eval_ekp,
}


def evaluate(inp: EvalInput, benefit_ids: list[str] | None = None) -> list[EligibilityResult]:
    """Evaluate benefits in catalog order (or the requested subset)."""
    out = []
    for bid, entry in catalog.entries().items():
        if benefit_ids is not None and bid not in benefit_ids:
            continue
        fn = EVALUATORS.get(bid)
        if fn is None:
            raise KeyError(f"no evaluator for benefit {bid}")
        out.append(fn(entry, inp))
    return out
