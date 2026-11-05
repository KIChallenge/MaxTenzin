"""Form sessions: start (prefill), next questions, validated patches, preview. Persisted in store('form_sessions')."""

from __future__ import annotations

import re
import uuid
from datetime import date

from fastapi import HTTPException
from pydantic import BaseModel

from app.contracts.common import SourceRef
from app.contracts.documents import DocumentAnalysis
from app.contracts.forms import FieldType, FieldValue, FormField, FormSession, NextQuestions
from app.contracts.identity import Person
from app.core.db import now_iso, store
from app.seed.loader import delegations_for
from app.services.forms.pdf import doctor_only_pdf_fields
from app.services.forms.prefill import prefill
from app.services.forms.spec import FieldSpec, FormSpec, get_spec

COLLECTION = "form_sessions"
DOCTOR_ONLY_DE = "Dieser Teil wird ausschließlich von der Ärztin bzw. dem Arzt ausgefüllt."


class PreviewItem(BaseModel):
    field_id: str
    label_de: str
    section: str
    value: str | bool | None
    source: SourceRef | None = None
    confirmed: bool = False
    required: bool = False
    missing: bool = False
    readonly_reason_de: str | None = None


class FormPreview(BaseModel):
    session_id: str
    form_id: str
    title_de: str
    status: str
    items: list[PreviewItem]
    missing_required: list[str]
    notice_de: str
    submit_info_de: str


def spec_or_404(form_id: str) -> FormSpec:
    spec = get_spec(form_id)
    if spec is None:
        raise HTTPException(404, "Formular nicht gefunden.")
    return spec


def start_session(spec: FormSpec, subject: Person, actor: Person, analysis: DocumentAnalysis | None = None) -> FormSession:
    delegation = next((d for d in delegations_for(subject.id) if d.grantee_id == actor.id), None)
    sess = FormSession(id=str(uuid.uuid4()), form_id=spec.form_id, subject_id=subject.id, actor_id=actor.id,
                       document_id=analysis.document_id if analysis else None,
                       values=prefill(spec, subject, actor, delegation, analysis), updated_at=now_iso())
    save(sess)
    return sess


def save(sess: FormSession) -> FormSession:
    sess.updated_at = now_iso()
    store.put(COLLECTION, sess.id, sess.model_dump(), subject_id=sess.subject_id)
    return sess


def load_session(session_id: str, subject_id: str) -> FormSession:
    data = store.get(COLLECTION, session_id)
    if not data or data.get("subject_id") != subject_id:
        raise HTTPException(404, "Formular-Sitzung nicht gefunden.")
    return FormSession(**data)


def _empty(fv: FieldValue | None) -> bool:
    return fv is None or fv.value is None or fv.value == "" or fv.value is False


def relevant(spec: FormSpec, f: FieldSpec, sess: FormSession) -> bool:
    c = f.when
    if c is None:
        return True
    if c.proxy is not None:
        return (sess.actor_id != sess.subject_id) == c.proxy
    cur = sess.values.get(c.field)
    val = cur.value if cur else None
    if c.one_of:
        return val in c.one_of
    if c.equals is None:
        return not _empty(cur)
    return val == c.equals


def _required_now(spec: FormSpec, f: FieldSpec, sess: FormSession) -> bool:
    return f.required and not f.readonly and relevant(spec, f, sess)


def _ordered(spec: FormSpec) -> list[FieldSpec]:
    order = {s: i for i, s in enumerate(spec.sections)}
    return sorted(spec.fields, key=lambda f: order[f.section])  # stable: keeps YAML order inside a section


def next_questions(spec: FormSpec, sess: FormSession, include_optional: bool = False) -> NextQuestions:
    required = [f for f in _ordered(spec) if _required_now(spec, f, sess)]
    missing = [f for f in required if _empty(sess.values.get(f.id))]
    questions: list[FormField] = [f.to_contract() for f in missing]
    if include_optional:
        questions += [f.to_contract() for f in _ordered(spec)
                      if f.recommended and not f.readonly and relevant(spec, f, sess) and _empty(sess.values.get(f.id))]
    return NextQuestions(session_id=sess.id, questions=questions,
                         progress=round(1 - len(missing) / max(1, len(required)), 3))


_DATE_DE = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$")
_TRUE = {"true", "ja", "yes", "1", "x"}
_FALSE = {"false", "nein", "no", "0", ""}


def _normalize_date(raw: str) -> str:
    raw = raw.strip()
    try:
        if m := _DATE_DE.match(raw):
            d = date(int(m[3]), int(m[2]), int(m[1]))
        else:
            d = date.fromisoformat(raw)
    except ValueError:
        raise ValueError("Bitte ein gültiges Datum im Format TT.MM.JJJJ angeben.") from None
    return d.strftime("%d.%m.%Y")


def validate_value(spec: FormSpec, f: FieldSpec, value):
    """Return the normalized value or raise ValueError with a German message."""
    if f.doctor_only or (f.pdf_target and f.pdf_target in doctor_only_pdf_fields(spec)):
        raise ValueError(DOCTOR_ONLY_DE)
    if f.readonly_reason_de:
        raise ValueError(f.readonly_reason_de)
    if value is None:
        return None
    if f.type == FieldType.checkbox:
        if isinstance(value, bool):
            return value
        if str(value).strip().lower() in _TRUE:
            return True
        if str(value).strip().lower() in _FALSE:
            return False
        raise ValueError("Bitte mit ja oder nein antworten.")
    if isinstance(value, bool):
        if f.type == FieldType.choice and {"ja", "nein"} <= set(f.options):
            return "ja" if value else "nein"
        raise ValueError("Bitte einen Text angeben, nicht ja/nein.")
    text = str(value).strip()
    if text == "":
        return None
    if f.type == FieldType.choice:
        match = next((o for o in f.options if o.lower() == text.lower()), None)
        if match is None:
            raise ValueError(f"Ungültige Auswahl. Möglich sind: {', '.join(f.options)}.")
        return match
    if f.type == FieldType.date:
        return _normalize_date(text)
    if f.compact:
        text = re.sub(r"\s+", "", text).upper()
    if len(text) > 2000:
        raise ValueError("Der Text ist zu lang (höchstens 2000 Zeichen).")
    return text


def apply_patch(spec: FormSpec, sess: FormSession, values: dict, confirm: bool) -> FormSession:
    errors: dict[str, str] = {}
    normalized = {}
    for fid, raw in values.items():
        f = spec.field(fid)
        if f is None:
            errors[fid] = "Unbekanntes Feld in diesem Formular."
            continue
        try:
            normalized[fid] = validate_value(spec, f, raw)
        except ValueError as e:
            errors[fid] = f"{f.label_de}: {e}"
    if errors:
        raise HTTPException(422, {"message_de": "Einige Angaben sind ungültig.", "fields": errors})
    for fid, v in normalized.items():
        # a user/agent-entered value replaces any prefill source; it is the person's own statement
        sess.values[fid] = FieldValue(value=v, source=None, confirmed=confirm)
    if sess.status == "rendered":
        sess.status = "draft"
    if not next_questions(spec, sess).questions:
        sess.status = "ready"
    return save(sess)


def relevant_values(spec: FormSpec, sess: FormSession) -> dict[str, FieldValue]:
    """Values that belong in the PDF: answers to questions that no longer apply are left out."""
    return {f.id: sess.values[f.id] for f in spec.fields if f.id in sess.values and relevant(spec, f, sess)}


def preview(spec: FormSpec, sess: FormSession) -> FormPreview:
    items, missing = [], []
    for f in _ordered(spec):
        if not relevant(spec, f, sess):
            continue
        fv = sess.values.get(f.id) or FieldValue(value=None)
        is_missing = _required_now(spec, f, sess) and _empty(fv)
        if is_missing:
            missing.append(f.id)
        if _empty(fv) and not is_missing and not f.readonly:
            continue
        items.append(PreviewItem(field_id=f.id, label_de=f.label_de, section=f.section, value=fv.value, source=fv.source,
                                 confirmed=fv.confirmed, required=f.required, missing=is_missing,
                                 readonly_reason_de=f.readonly_reason_de))
    return FormPreview(
        session_id=sess.id, form_id=spec.form_id, title_de=spec.title_de, status=sess.status, items=items,
        missing_required=missing,
        notice_de="Dies ist ein Entwurf. Bitte prüfen Sie alle Angaben, unterschreiben Sie selbst und reichen Sie den "
                  "Antrag selbst ein. Es wird nichts automatisch übermittelt.",
        submit_info_de=spec.submit_info_de)
