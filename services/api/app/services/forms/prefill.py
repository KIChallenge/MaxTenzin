"""Prefill engine: person profile, actor (Vertretung), delegation and document analysis -> FieldValue + SourceRef.

Rules
- Every prefilled value carries a SourceRef and starts unconfirmed (the person reviews it in wizard/chat/preview).
- From documents we take ONLY non-medical, explicitly stated facts (file name, document type, extracted person data).
  Medical content (e.g. PAL080 "Leiden") is never derived, paraphrased or interpreted: it is asked from the person.
- Doctor-only fields are never prefilled (enforced in spec validation).
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
        "attachment": f"Kopie: {a.filename}",
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


def _profile_src(p: Person, key: str, who: str) -> SourceRef:
    return SourceRef(kind=SourceKind.external, label=f"ID Austria Stammdaten ({who}, Demo)", ref=f"person:{p.id}#{key}")


def prefill(spec: FormSpec, subject: Person, actor: Person, delegation: Delegation | None = None,
            analysis: DocumentAnalysis | None = None, today: date | None = None) -> dict[str, FieldValue]:
    """Initial session values. Fields without a usable prefill start empty (value None)."""
    proxy = actor.id != subject.id
    subj, act = person_keys(subject), person_keys(actor)
    deleg = delegation_keys(delegation) if delegation else {}
    doc = document_keys(analysis) if analysis else {}
    today = today or date.today()
    values: dict[str, FieldValue] = {}

    for f in spec.fields:
        values[f.id] = FieldValue(value=None)
        if not f.prefill or f.doctor_only:
            continue
        if f.when and f.when.proxy is not None and f.when.proxy != proxy:
            continue
        kind, _, key = f.prefill.partition(".")
        value: str | None = None
        src: SourceRef | None = None
        if f.prefill.startswith("const:"):
            value = f.prefill.removeprefix("const:")
            src = SourceRef(kind=SourceKind.form, label=f"Vorschlag – bitte prüfen ({spec.form_version})", ref=spec.form_id)
        elif kind == "profile":
            value, src = subj.get(key), _profile_src(subject, key, f"{subject.first_name} {subject.last_name}")
        elif kind == "actor" and proxy:
            value, src = act.get(key), _profile_src(actor, key, f"{actor.first_name} {actor.last_name}")
        elif kind == "delegation" and proxy and delegation:
            value = deleg.get(key)
            src = SourceRef(kind=SourceKind.external, label=f"Vertretung im ID-Austria-Profil ({delegation.relation})",
                            ref=f"delegation:{delegation.id}", quote=delegation.consent_note or None)
        elif kind == "document" and analysis:
            value = doc.get(key)
            fact = next((x for x in analysis.facts if x.key == key), None)
            src = (SourceRef(kind=SourceKind.document, label=f"{analysis.filename}, S. {fact.page}",
                             ref=f"document:{analysis.document_id}#page={fact.page}", quote=fact.quote)
                   if fact else SourceRef(kind=SourceKind.document, label=analysis.filename,
                                          ref=f"document:{analysis.document_id}"))
        elif kind == "system" and key in ("today", "city_today"):
            value = today.strftime("%d.%m.%Y")
            if key == "city_today":
                value = f"{subj['city']}, {value}"
            src = SourceRef(kind=SourceKind.form, label="Heutiges Datum – bitte beim Unterschreiben prüfen", ref="today")
        if value in (None, ""):
            continue
        if f.options and value not in f.options:
            continue  # never put a value into a choice that the official form does not offer
        if f.type.value == "checkbox":
            value = value in ("ja", "true", "1")
        values[f.id] = FieldValue(value=value, source=src, confirmed=False)
    return values
