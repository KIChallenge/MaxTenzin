"""Lebenslage: episode store, status logic, document suggestions and the deterministic effects engine.

Pure functions (no FastAPI) so the integrator can wire them elsewhere:
- situation_facts(subject_id)      -> eligibility facts from ACTIVE confirmed episodes
- situation_reminders(subject_id)  -> reminder effects (Meldepflichten, Kontrolltermin) for the inbox
- resolve_prefill(subject_id, key) -> (value, SourceRef) for the forms prefill rule kind `situation.<key>`

Only CONFIRMED episodes (person-entered, or suggestions after explicit consent) have effects. Suggestions never do.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from app.contracts.common import SourceKind, SourceRef
from app.contracts.documents import DocumentAnalysis, DocumentType, RecommendationCategory
from app.contracts.situation import Effect, EffectKind, Episode, EpisodeStatus, EpisodeType, SituationOverview
from app.core.db import store
from app.core.knowledge import yaml_file

COLL = "episodes"
ANALYSES = "document_analyses"   # owned by WS-D (read only here)
CONFIRMED = "confirmed"          # stored base state of person-entered / consented episodes
EFFECTIVE = (EpisodeStatus.planned, EpisodeStatus.active, EpisodeStatus.ended)
STAY_DE = {"hospital": "Spitalsaufenthalt", "rehab_inpatient": "Reha-Aufenthalt", "cure": "Kuraufenthalt",
           "nursing_home": "Pflegeheim-Aufnahme"}
MONTHS = "Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember"


def cfg() -> dict:
    return yaml_file("situation.yaml")


# ---------------------------------------------------------------------------------------------------------- dates
def parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", s.strip())
        return date(int(m[3]), int(m[2]), int(m[1])) if m else None


def date_de(d: date | str | None) -> str:
    if isinstance(d, str):
        d = parse_date(d)
    return d.strftime("%d.%m.%Y") if d else ""


# ---------------------------------------------------------------------------------------------------------- store
def compute_status(raw: dict, today: date) -> EpisodeStatus:
    """suggested/rejected are untouched; confirmed episodes: ended/planned/active from dates vs today."""
    st = raw.get("status")
    if st in (EpisodeStatus.suggested, EpisodeStatus.rejected):
        return EpisodeStatus(st)
    manual = raw.get("manual_status")
    start, end = parse_date(raw.get("start")), parse_date(raw.get("end"))
    if manual == EpisodeStatus.ended or (end and end < today):
        return EpisodeStatus.ended
    if start and start > today:
        return EpisodeStatus.planned
    if start:
        return EpisodeStatus.active
    return EpisodeStatus(manual) if manual in (EpisodeStatus.planned, EpisodeStatus.active) else EpisodeStatus.active


def to_episode(raw: dict, today: date) -> Episode:
    return Episode.model_validate({**raw, "status": compute_status(raw, today)})


def raw_episodes(subject_id: str) -> list[dict]:
    return store.list(COLL, subject_id=subject_id)


def get_raw(subject_id: str, episode_id: str) -> dict | None:
    raw = store.get(COLL, episode_id)
    return raw if raw and raw.get("subject_id") == subject_id else None


def put_raw(raw: dict) -> dict:
    return store.put(COLL, raw["id"], raw, subject_id=raw["subject_id"])


def episodes(subject_id: str, today: date | None = None) -> list[Episode]:
    today = today or date.today()
    return [to_episode(r, today) for r in raw_episodes(subject_id)]


def confirmed(subject_id: str, today: date) -> list[Episode]:
    return [e for e in episodes(subject_id, today) if e.status in EFFECTIVE]


def title_for(type_: EpisodeType | str, subtype: str | None) -> str:
    if str(type_) == EpisodeType.therapy and subtype:
        st = cfg()["therapy_subtypes"].get(subtype)
        if st:
            return st["title_de"]
    return cfg()["types"][str(type_)]["title_de"]


def person_source(actor_name: str, today: date) -> SourceRef:
    return SourceRef(kind=SourceKind.external, label=f"Angabe von {actor_name}, {date_de(today)}", ref="situation:person")


# ---------------------------------------------------------------------------------------------------------- analyses
def load_analysis(subject_id: str, document_id: str) -> DocumentAnalysis | None:
    """Stored analysis of this subject, else the hand-verified demo golden (same fallback as documents/benefits)."""
    own = {a["document_id"]: a for a in store.list(ANALYSES, subject_id=subject_id)}
    if document_id in own:
        return DocumentAnalysis.model_validate(own[document_id])
    from app.services.documents import goldens
    from app.services.documents.extract import enforce_boundary, from_golden

    g = goldens.by_demo_id(document_id)
    if g and g.get("demo_subject_id") == subject_id:
        return enforce_boundary(from_golden(g, document_id))
    from app.fixtures import ANNA_ANALYSIS

    return ANNA_ANALYSIS if document_id == ANNA_ANALYSIS.document_id and subject_id == "anna" else None


def document_pages(subject_id: str, document_id: str) -> list[str]:
    """Page texts of an uploaded/seeded PDF owned by the subject (empty if not available, e.g. in tests)."""
    from app.services.documents import storage

    meta = storage.get_meta(document_id)
    if not meta or meta.get("owner_id") != subject_id:
        return []
    data = storage.load_pdf(document_id)
    if not data:
        return []
    from app.services.documents.pdf import page_texts

    return page_texts(data)


# ---------------------------------------------------------------------------------------------------------- suggestions
def _norm(s: str) -> str:
    return " ".join(s.split())


def _doc_src(a: DocumentAnalysis, quote: str | None, page: int | None) -> SourceRef:
    if page:
        return SourceRef(kind=SourceKind.document, label=f"{a.filename}, S. {page}",
                         ref=f"document:{a.document_id}#page={page}", quote=quote)
    return SourceRef(kind=SourceKind.document, label=a.filename, ref=f"document:{a.document_id}")


THERAPY_PAGE_RE = re.compile(r"Die Bestrahlung erfolgt ambulant[^.]*\.(?:\s*Der Abschluss[^.]*\.)?")
THERAPY_QUOTE_RE = re.compile(r"Strahlentherapie|Bestrahlung")
ESTIMATE_RE = re.compile(rf"Abschluss[^.]*?\b((?:Anfang|Mitte|Ende) (?:{MONTHS}) \d{{4}})")
HOME_RE = re.compile(r"Hauskrankenpflege|mobile[rn]? Pflege|Körperpflege|Alltagshilfe")


def suggest_from_analysis(a: DocumentAnalysis, pages: list[str] | None = None) -> list[dict]:
    """Deterministic: discharge letter -> hospital, home_care, therapy (strahlentherapie), rehab (planned).

    Only the episode TYPE (+ administrative dates) is taken over; every suggestion carries a verbatim quote + page.
    Returns partial raw episodes keyed by `rule` (used for idempotent ids).
    """
    out: list[dict] = []
    if a.doc_type != DocumentType.discharge_letter:
        return out
    facts = {f.key: f for f in a.facts}
    discharge = facts.get("discharge_date")
    discharge_iso = parse_date(discharge.value).isoformat() if discharge and parse_date(discharge.value) else None
    admission = facts.get("admission_date")
    inst = facts.get("institution") or facts.get("department")
    hosp_src = _doc_src(a, discharge.quote, discharge.page) if discharge else _doc_src(a, None, None)
    out.append({"rule": "hospital", "type": EpisodeType.hospital,
                "start": parse_date(admission.value).isoformat() if admission and parse_date(admission.value) else None,
                "end": discharge_iso, "institution": inst.value if inst else None, "source": hosp_src,
                "institution_source": _doc_src(a, inst.quote, inst.page) if inst else None,
                "manual_status": EpisodeStatus.ended,
                "note_de": "Aus dem Entlassungsbrief. Das Aufnahmedatum steht nicht im Dokument – bitte ergänzen."
                if not admission else None})

    home = next((r for r in a.recommendations if r.category == RecommendationCategory.care and HOME_RE.search(r.quote)),
                None)
    if home:
        out.append({"rule": "home_care", "type": EpisodeType.home_care, "start": discharge_iso,
                    "source": _doc_src(a, home.quote, home.page),
                    "note_de": "Im Entlassungsbrief wird Unterstützung zu Hause empfohlen. Bitte bestätigen, wenn "
                               "die Unterstützung (z. B. mobile Pflege, Angehörige) besteht."})

    candidates: list[tuple[str, int]] = []
    for i, text in enumerate(pages or [], start=1):
        m = THERAPY_PAGE_RE.search(_norm(text))
        if m:
            candidates.append((m.group(0), i))
    candidates += [(r.quote, r.page) for r in a.recommendations if THERAPY_QUOTE_RE.search(r.quote)]
    if candidates:
        quote, page = next(((q, p) for q, p in candidates if "ambulant" in q), candidates[0])
        est = next((m.group(1) for q, _ in candidates if (m := ESTIMATE_RE.search(q))), None)
        if est and not ESTIMATE_RE.search(quote):
            quote, page = next((q, p) for q, p in candidates if ESTIMATE_RE.search(q))
        out.append({"rule": "therapy", "type": EpisodeType.therapy, "subtype": "strahlentherapie",
                    "end_estimate_de": est, "source": _doc_src(a, quote, page),
                    "manual_status": EpisodeStatus.active,
                    "note_de": "Im Entlassungsbrief wird eine Strahlentherapie genannt. Bitte bestätigen, ob sie "
                               "derzeit läuft, und den Zeitraum ergänzen."})

    reha = next((r for r in a.recommendations if r.category == RecommendationCategory.rehabilitation), None)
    if reha:
        inpatient = "stationär" in reha.quote.lower() or "ambulant" not in reha.quote.lower()
        out.append({"rule": "rehab", "type": EpisodeType.rehab_inpatient if inpatient else EpisodeType.rehab_outpatient,
                    "source": _doc_src(a, reha.quote, reha.page), "manual_status": EpisodeStatus.planned,
                    "note_de": "Im Entlassungsbrief wird die Prüfung einer Reha empfohlen. Beginn und Dauer legt der "
                               "Kostenträger fest – bitte ergänzen, sobald bekannt."})
    return out


def suggestion_id(document_id: str, rule: str) -> str:
    return f"sug-{document_id}-{rule}"


# ---------------------------------------------------------------------------------------------------------- effects
def pflegegeld_involved(subject_id: str, facts: dict | None = None) -> bool:
    """Pflegegeld is received or being applied for: fact, a Mein-Fall step for pflegegeld, or a PAL 080 form session."""
    f = facts or {}
    if f.get("receives_pflegegeld") or f.get("pflegegeld_applied"):
        return True
    for case in store.list("cases", subject_id=subject_id):
        if any(s.get("benefit_id") == "pflegegeld" for s in case.get("steps", [])):
            return True
    return any(s.get("form_id") == "pva_pflegegeld_pal080" for s in store.list("form_sessions", subject_id=subject_id))


def _source(key: str) -> SourceRef | None:
    spec = cfg()["sources"][key]
    if "law" in spec:
        try:
            from app.services.legal.service import source_ref

            return source_ref(spec["law"], spec["nr"], spec.get("abs"))
        except KeyError:
            return None
    return SourceRef(kind=SourceKind(spec["kind"]), label=spec["label"], ref=spec["ref"], quote=spec.get("quote"))


def _meldepflicht_due(e: Episode) -> date | None:
    base = parse_date(e.start) or parse_date(e.end)
    return base + timedelta(days=28) if base else None


def _relevant_deadline(e: Episode, due: date | None, today: date) -> bool:
    """Show running/planned stays always; ended stays while the deadline is near (incl. 90 days overdue)."""
    if e.status != EpisodeStatus.ended:
        return True
    return due is not None and due >= today - timedelta(days=90)


def _subtype_de(e: Episode) -> str:
    st = cfg()["therapy_subtypes"].get(e.subtype or "")
    return st["title_de"] if st else (e.subtype or "Therapie")


def facts_from(eps: list[Episode]) -> list[Effect]:
    out: list[Effect] = []
    rules = cfg()["facts"]
    for e in eps:
        if e.status != EpisodeStatus.active or str(e.type) not in rules:
            continue
        r = rules[str(e.type)]
        if e.type == EpisodeType.therapy:
            st = cfg()["therapy_subtypes"].get(e.subtype or "")
            if not st or not st["fact"]:
                continue
            value: str | bool = e.subtype
        else:
            value = True
        out.append(Effect(kind=EffectKind.fact, episode_id=e.id, key=r["key"], value=value, source=e.source,
                          title_de=r["title_de"].format(subtype_de=_subtype_de(e))))
    return out


def _followup_source(subject_id: str, e: Episode) -> SourceRef | None:
    m = re.match(r"document:([^#]+)", e.source.ref or "")
    if not m:
        return None
    a = load_analysis(subject_id, m.group(1))
    rec = next((r for r in (a.recommendations if a else []) if r.category == RecommendationCategory.follow_up), None)
    return _doc_src(a, rec.quote, rec.page) if rec else None


def reminders_from(subject_id: str, eps: list[Episode], today: date, pflegegeld: bool) -> list[Effect]:
    rules = cfg()["rules"]
    out: list[Effect] = []
    for e in eps:
        t = str(e.type)
        for rid in ("meldepflicht_stay", "meldepflicht_pflegeheim"):
            r = rules[rid]
            if t not in r["applies_to"] or not pflegegeld:
                continue
            due = _meldepflicht_due(e)
            if not _relevant_deadline(e, due, today):
                continue
            detail = r["detail_de"].strip()
            if due and due < today:
                detail += " Die Frist ist bereits abgelaufen – bitte umgehend melden."
            out.append(Effect(kind=EffectKind.reminder, episode_id=e.id, key=f"meldepflicht:{t}",
                              title_de=r["title_de"].format(stay_de=STAY_DE.get(t, "Aufenthalt")), detail_de=detail,
                              due_date=due.isoformat() if due else None, value="pflegegeld", source=_source(r["source"])))
        r = rules["hausarzt_kontrolle"]
        end = parse_date(e.end)
        if (t in r["applies_to"] and e.status == EpisodeStatus.ended and end
                and today - end <= timedelta(days=r["after_end_days"])):
            src = _followup_source(subject_id, e)
            out.append(Effect(kind=EffectKind.reminder, episode_id=e.id, key=f"appointment:{r['appointment_topic']}",
                              value=r["appointment_topic"], title_de=r["title_de"],
                              detail_de=r["detail_de_documented"] if src else r["detail_de"], source=src or e.source))
    return out


def hints_from(eps: list[Episode], pflegegeld: bool) -> list[Effect]:
    r = cfg()["rules"]["pflegegeld_ruht"]
    out: list[Effect] = []
    if not pflegegeld:
        return out
    src = _source(r["source"])
    if src is None:   # never show it without the paragraph
        return out
    for e in eps:
        if str(e.type) in r["applies_to"] and e.status in (EpisodeStatus.active, EpisodeStatus.planned):
            out.append(Effect(kind=EffectKind.hint, episode_id=e.id, key="pflegegeld_ruht", title_de=r["title_de"],
                              detail_de=" ".join(r["detail_de"].split()), source=src))
    return out


def case_steps_from(eps: list[Episode], today: date, pflegegeld: bool) -> list[dict]:
    """Mein-Fall steps (deterministic ids for idempotency)."""
    rules = cfg()["rules"]
    out: list[dict] = []
    for e in eps:
        t = str(e.type)
        for rid in ("meldepflicht_stay", "meldepflicht_pflegeheim"):
            r = rules[rid]
            if t not in r["applies_to"] or not pflegegeld:
                continue
            due = _meldepflicht_due(e)
            if not _relevant_deadline(e, due, today):
                continue
            title = (r["case_step_de"].format(stay_de=STAY_DE.get(t, "Aufenthalt"), due_de=date_de(due)) if due
                     else r["case_step_undated_de"].format(stay_de=STAY_DE.get(t, "Aufenthalt")))
            out.append({"id": f"sit-{e.id}-{rid}", "episode_id": e.id, "title_de": title, "responsible_de": r["responsible_de"],
                        "benefit_id": "pflegegeld", "due_date": due.isoformat() if due else None,
                        "source": _source(r["source"])})
        r = rules["reha_antreten"]
        if t in r["applies_to"] and e.status == EpisodeStatus.planned:
            start = parse_date(e.start)
            out.append({"id": f"sit-{e.id}-reha_antreten", "episode_id": e.id,
                        "title_de": r["case_step_dated_de"].format(start_de=date_de(start)) if start
                        else r["case_step_de"], "responsible_de": r["responsible_de"], "benefit_id": None,
                        "due_date": start.isoformat() if start else None, "source": e.source})
        r = rules["nach_reha_pflegebedarf"]
        if t in r["applies_to"] and pflegegeld and e.status in (EpisodeStatus.planned, EpisodeStatus.active):
            out.append({"id": f"sit-{e.id}-nach_reha", "episode_id": e.id, "title_de": r["case_step_de"],
                        "responsible_de": r["responsible_de"], "benefit_id": "pflegegeld",
                        "due_date": e.end, "source": e.source})
    return out


# ---------------------------------------------------------------------------------------------------------- prefill
def prefill_keys(subject_id: str, today: date | None = None) -> dict[str, tuple[str, SourceRef]]:
    """Keys for the forms rule kind `situation.<key>`. Value "" = situation knows the stay but not this detail
    (the document fallback is then NOT used, so values of different stays are never mixed)."""
    today = today or date.today()
    p = cfg()["prefill"]
    eps = confirmed(subject_id, today)
    inst_src = {r["id"]: SourceRef.model_validate(r["institution_source"]) for r in raw_episodes(subject_id)
                if r.get("institution_source")}

    def inst(e: Episode) -> tuple[str, SourceRef]:
        """Institution with its own quote when it came from a document (e.g. the department line)."""
        return (e.institution or "", inst_src.get(e.id, e.source) if e.institution else e.source)

    keys: dict[str, tuple[str, SourceRef]] = {}
    lookback = today - timedelta(days=p["stay_lookback_days"])
    stays = [e for e in eps if str(e.type) in p["stay_types"] and (
        e.status == EpisodeStatus.active or (e.status == EpisodeStatus.ended and (parse_date(e.end) or today) >= lookback))]
    stays.sort(key=lambda e: (parse_date(e.end) or today, parse_date(e.start) or date.min), reverse=True)
    if stays:
        keys["stay.any"] = ("ja", stays[0].source)
    for i, e in enumerate(stays[:2], start=1):
        keys[f"stay{i}.start"] = (date_de(e.start), e.source)
        keys[f"stay{i}.end"] = (date_de(e.end), e.source)
        keys[f"stay{i}.institution"] = inst(e)
    hosp = next((e for e in stays if e.type == EpisodeType.hospital), None)
    if hosp:
        keys["hospital.start"] = (date_de(hosp.start), hosp.source)
        keys["hospital.end"] = (date_de(hosp.end), hosp.source)
        keys["hospital.institution"] = inst(hosp)
    years5 = today.replace(year=today.year - p["rehab_lookback_years"])
    rehabs = [e for e in eps if e.type in (EpisodeType.rehab_inpatient, EpisodeType.cure)
              and e.status == EpisodeStatus.ended and (parse_date(e.end) or today) >= years5]
    rehabs.sort(key=lambda e: parse_date(e.end) or today, reverse=True)
    if rehabs:
        keys["rehab5y.any"] = ("ja", rehabs[0].source)
    for i, e in enumerate(rehabs[:2], start=1):
        when = " – ".join(x for x in (date_de(e.start), date_de(e.end)) if x)
        keys[f"rehab5y_{i}.when"] = (when, e.source)
        keys[f"rehab5y_{i}.where"] = (e.institution or "", e.source)
    therapy = next((e for e in eps if e.type == EpisodeType.therapy and e.status == EpisodeStatus.active), None)
    if therapy:
        keys["therapy.kind"] = (therapy.title_de, therapy.source)
        keys["therapy.institution"] = (therapy.institution or "", therapy.source)
    return keys


def resolve_prefill(subject_id: str, key: str, today: date | None = None) -> tuple[str, SourceRef] | None:
    return prefill_keys(subject_id, today).get(key)


PREFILL_FORMS = ("pva_pflegegeld_pal080", "sv_kur_reha", "oegk_fahrtkosten_wien")


def prefill_effects(subject_id: str, today: date) -> list[Effect]:
    from app.services.forms.spec import get_spec

    keys = prefill_keys(subject_id, today)
    out: list[Effect] = []
    for form_id in PREFILL_FORMS:
        spec = get_spec(form_id)
        for f in spec.fields if spec else []:
            alt = next((x.removeprefix("situation.") for x in (f.prefill or "").split("|")
                        if x.startswith("situation.")), None)
            hit = keys.get(alt) if alt else None
            if hit and hit[0]:
                out.append(Effect(kind=EffectKind.prefill, key=f"{form_id}:{f.id}", value=hit[0], source=hit[1],
                                  title_de=f"{spec.title_de}: {f.label_de}"))
    return out


# ---------------------------------------------------------------------------------------------------------- overview
def _summary(cur: list[Episode], upcoming: list[Episode], n_suggestions: int) -> str:
    c = cfg()
    order = {t: i for i, t in enumerate(c["summary_order"])}
    parts: list[str] = []
    for e in sorted(cur, key=lambda e: order.get(str(e.type), 99)):
        if e.type == EpisodeType.therapy and e.subtype in c["therapy_subtypes"]:
            phrase = c["therapy_subtypes"][e.subtype]["current_de"]
        else:
            phrase = c["types"][str(e.type)]["current_de"]
        if phrase not in parts:
            parts.append(phrase)
    for e in sorted(upcoming, key=lambda e: order.get(str(e.type), 99)):
        phrase = c["types"][str(e.type)]["planned_de"]
        if phrase not in parts:
            parts.append(phrase)
    if not parts:
        text = "Keine aktuelle Lebenslage eingetragen"
        if n_suggestions:
            text += f" – {n_suggestions} Vorschläge aus Dokumenten warten auf Ihre Bestätigung"
        return text
    s = " · ".join(parts)
    return s[0].upper() + s[1:]


def overview(subject_id: str, today: date | None = None, facts: dict | None = None) -> SituationOverview:
    today = today or date.today()
    eps = episodes(subject_id, today)

    def by(st: EpisodeStatus) -> list[Episode]:
        return sorted([e for e in eps if e.status == st], key=lambda e: (e.start or "", e.end or ""))

    cur, upcoming, past, sugg = by(EpisodeStatus.active), by(EpisodeStatus.planned), by(EpisodeStatus.ended), \
        by(EpisodeStatus.suggested)
    past.sort(key=lambda e: e.end or "", reverse=True)
    effects = effects_for(subject_id, [e for e in eps if e.status in EFFECTIVE], today, facts)
    fact_dict = {f.key: f.value for f in effects if f.kind == EffectKind.fact}
    return SituationOverview(subject_id=subject_id, as_of=today.isoformat(), current=cur, upcoming=upcoming, past=past,
                             suggestions=sugg, effects=effects, facts=fact_dict,
                             summary_de=_summary(cur, upcoming, len(sugg)))


def effects_for(subject_id: str, eps: list[Episode], today: date, facts: dict | None = None) -> list[Effect]:
    pg = pflegegeld_involved(subject_id, facts)
    out = reminders_from(subject_id, eps, today, pg) + facts_from(eps) + hints_from(eps, pg)
    out += prefill_effects(subject_id, today) if eps else []
    for step in case_steps_from(eps, today, pg):
        out.append(Effect(kind=EffectKind.case_step, episode_id=step["episode_id"],
                          title_de=step["title_de"], key=step["id"], due_date=step["due_date"],
                          value=step["benefit_id"], source=step["source"]))
    return out


# ---------------------------------------------------------------------------------------------------------- public API
def situation_facts(subject_id: str, today: date | None = None) -> dict:
    """Eligibility facts from active confirmed episodes, e.g. {'treatment_type': 'strahlentherapie'}."""
    today = today or date.today()
    return {f.key: f.value for f in facts_from(confirmed(subject_id, today))}


def situation_reminders(subject_id: str, today: date | None = None, facts: dict | None = None) -> list[Effect]:
    """Reminder effects (Meldepflichten with due date, Kontrolltermin) for the inbox/notifications."""
    today = today or date.today()
    eps = confirmed(subject_id, today)
    return reminders_from(subject_id, eps, today, pflegegeld_involved(subject_id, facts))


def latest_case(subject_id: str, cases: list[dict]) -> dict | None:
    own = [c for c in cases if c.get("subject_id") == subject_id]
    return max(own, key=lambda c: c.get("created_at", "")) if own else None


def add_case_steps(case: dict, steps: list[dict]) -> list[str]:
    """Append missing situation steps to a case dict (idempotent by step id). Returns the ids added."""
    have = {s["id"] for s in case.get("steps", [])}
    added = []
    for s in steps:
        if s["id"] in have:
            continue
        src = s.get("source")
        case.setdefault("steps", []).append({
            "id": s["id"], "title_de": s["title_de"], "responsible_de": s["responsible_de"], "status": "open",
            "benefit_id": s.get("benefit_id"), "form_session_id": None, "due_date": s.get("due_date"),
            "source": src.model_dump() if isinstance(src, SourceRef) else src})
        added.append(s["id"])
    return added
