"""Prefill engine: person profile, actor (Vertretung), delegation, Lebenslage (situation) and document analysis
-> FieldValue + SourceRef.

Rules
- Every prefilled value carries a SourceRef and starts unconfirmed (the person reviews it in wizard/chat/preview).
- From documents we take ONLY non-medical, explicitly stated facts (file name, document type, extracted person data).
  Medical content (e.g. PAL080 "Leiden") is never derived, paraphrased or interpreted: it is asked from the person.
- Doctor-only fields are never prefilled (enforced in spec validation).
- `situation.<key>` reads CONFIRMED Lebenslage episodes only (never suggestions); source = the episode's own source.
"""

from __future__ import annotations

from datetime import date

from app.contracts.common import SourceKind, SourceRef
from app.contracts.documents import DocumentAnalysis, DocumentType
from app.contracts.forms import FieldValue
from app.contracts.identity import Delegation, Person
from app.services.forms.spec import FormSpec

SEX_DE = {"w": "weiblich", "m": "männlich", "d": "divers/inter/offen"}


def date_de(iso: str) -> str:
    """'1948-03-14' -> '14.03.1948' (unchanged if not ISO)."""
    try:
        return date.fromisoformat(iso).strftime("%d.%m.%Y")
    except (TypeError, ValueError):
        return iso


def person_keys(p: Person) -> dict[str, str]:
    a = p.address
    return {
        "first_name": p.first_name,
        "last_name": p.last_name,
        "full_name": f"{p.first_name} {p.last_name}",
        "full_name_last_first": f"{p.last_name} {p.first_name}",
        "birth_date": date_de(p.birth_date),
        "birth_year": p.birth_date[:4],
        "sex_de": SEX_DE.get(p.sex, ""),
        "sex_code": p.sex,
        "svnr": p.svnr,
        "svnr_digits": p.svnr.replace(" ", ""),
        "insurer": p.insurer,
        "street": a.street,
        "house": a.house,
        "zip": a.zip,
        "city": a.city,
        "country": a.country,
        "address_line": f"{a.street} {a.house}, {a.zip} {a.city}".replace(" ,", ","),
        "phone": p.phone,
        "email": p.email,
        "marital_status": p.marital_status,
        "citizenship": p.citizenship,
        "citizenship_choice": "Österreich" if p.citizenship == "Österreich" else "andere",
        "citizenship_other": "" if p.citizenship == "Österreich" else p.citizenship,
    }


def delegation_keys(d: Delegation) -> dict[str, str]:
    legal = any(w in d.relation.lower() for w in ("obsorge", "erwachsenenvertretung", "kurator"))
    return {
        "relation": d.relation,
        "representation": "gesetzliche Vertretung" if legal else "bevollmächtigt",
        "proof": "liegt bei",
        "is_representative": "ja",
        "consent_note": d.consent_note,
    }


def document_keys(a: DocumentAnalysis) -> dict[str, str]:
    keys = {
        "filename": a.filename,
        "attachment": "Kopie des Entlassungsbefunds" if a.doc_type == DocumentType.discharge_letter
        else f"Kopie: {a.filename}",
        "hospital_stay": "ja" if a.doc_type == DocumentType.discharge_letter else "",
    }
    for fact in a.facts:
        keys[fact.key] = fact.value
    for k in ("first_name", "last_name", "insurer"):
        v = getattr(a.person, k)
        if v:
            keys[f"person.{k}"] = v
    if a.person.birth_date:
        keys["person.birth_date"] = date_de(a.person.birth_date)
    return keys


ID_AUSTRIA_KEYS = {"first_name", "last_name", "full_name", "full_name_last_first", "birth_date", "birth_year"}
ZMR_KEYS = {"street", "house", "zip", "city", "country", "address_line"}
ECARD_KEYS = {"svnr", "svnr_digits", "insurer"}


def _profile_src(p: Person, key: str, who: str) -> SourceRef:
    """Honest provenance: ID Austria only provides identity (+ ZMR main residence with consent); the rest is profile data."""
    if key in ID_AUSTRIA_KEYS:
        label = f"ID Austria ({who}, Demo)"
    elif key in ZMR_KEYS:
        label = f"ID Austria – Hauptwohnsitz laut ZMR ({who}, Demo)"
    elif key in ECARD_KEYS:
        label = f"e-card / Sozialversicherung ({who}, Demo)"
    else:
        label = f"Profilangaben – bitte prüfen ({who}, Demo)"
    return SourceRef(kind=SourceKind.external, label=label, ref=f"person:{p.id}#{key}")


def _situation_keys(subject: Person, actor: Person, today: date) -> dict[str, tuple[str, SourceRef]]:
    """Lebenslage (WS-S): confirmed episodes only, and only if the actor may see the subject's situation."""
    from app.contracts.identity import Scope
    from app.core.auth import effective_scopes
    from app.services.situation.service import prefill_keys

    if Scope.manage_situation not in effective_scopes(actor.id, subject.id):
        return {}
    return prefill_keys(subject.id, today)


def prefill(spec: FormSpec, subject: Person, actor: Person, delegation: Delegation | None = None,
            analysis: DocumentAnalysis | None = None, today: date | None = None) -> dict[str, FieldValue]:
    """Initial session values. Fields without a usable prefill start empty (value None).

    A rule may list alternatives separated by "|" (e.g. "situation.stay1.end|document.discharge_date"): the first
    alternative that knows the value wins. A known-but-empty value ("") stops the chain (never mix two sources).
    """
    proxy = actor.id != subject.id
    subj, act = person_keys(subject), person_keys(actor)
    deleg = delegation_keys(delegation) if delegation else {}
    doc = document_keys(analysis) if analysis else {}
    today = today or date.today()
    situation: dict[str, tuple[str, SourceRef]] | None = None
    values: dict[str, FieldValue] = {}

    def resolve(rule: str) -> tuple[str | None, SourceRef | None]:
        nonlocal situation
        kind, _, key = rule.partition(".")
        if rule.startswith("const:"):
            return rule.removeprefix("const:"), SourceRef(kind=SourceKind.form, ref=spec.form_id,
                                                          label=f"Vorschlag – bitte prüfen ({spec.form_version})")
        if kind == "profile":
            return subj.get(key), _profile_src(subject, key, f"{subject.first_name} {subject.last_name}")
        if kind == "actor" and proxy:
            return act.get(key), _profile_src(actor, key, f"{actor.first_name} {actor.last_name}")
        if kind == "delegation" and proxy and delegation:
            return deleg.get(key), SourceRef(kind=SourceKind.external, ref=f"delegation:{delegation.id}",
                                             label=f"Vertretung im ID-Austria-Profil ({delegation.relation})",
                                             quote=delegation.consent_note or None)
        if kind == "document" and analysis:
            fact = next((x for x in analysis.facts if x.key == key), None)
            src = (SourceRef(kind=SourceKind.document, label=f"{analysis.filename}, S. {fact.page}",
                             ref=f"document:{analysis.document_id}#page={fact.page}", quote=fact.quote)
                   if fact else SourceRef(kind=SourceKind.document, label=analysis.filename,
                                          ref=f"document:{analysis.document_id}"))
            return doc.get(key), src
        if kind == "situation":
            if situation is None:
                situation = _situation_keys(subject, actor, today)
            hit = situation.get(key)
            return hit if hit else (None, None)
        if kind == "system" and key in ("today", "city_today"):
            value = today.strftime("%d.%m.%Y")
            if key == "city_today":
                value = f"{subj['city']}, {value}"
            return value, SourceRef(kind=SourceKind.form, label="Heutiges Datum – bitte beim Unterschreiben prüfen",
                                    ref="today")
        return None, None

    for f in spec.fields:
        values[f.id] = FieldValue(value=None)
        if not f.prefill or f.doctor_only:
            continue
        if f.when and f.when.proxy is not None and f.when.proxy != proxy:
            continue
        value: str | None = None
        src: SourceRef | None = None
        for rule in f.prefill.split("|"):
            value, src = resolve(rule.strip())
            if value is not None:
                break
        if value == "" and src is not None and f.blank_from_prefill:
            values[f.id] = FieldValue(value="", source=src, confirmed=False)   # known: leave empty
            continue
        if value in (None, ""):
            continue
        if f.options and value not in f.options:
            continue  # never put a value into a choice that the official form does not offer
        if f.type.value == "checkbox":
            value = value in ("ja", "true", "1")
        values[f.id] = FieldValue(value=value, source=src, confirmed=False)
    return values
