"""Form schema (knowledge/forms/<form_id>.yaml) -> FormDefinition (contract) + PDF mapping kept service-internal.

One schema, two clients: the wizard UI and the AI agent both read the same FormDefinition and fill the same session.
The PDF mapping (AcroForm names, export values, overflow lines) and prefill rules never leave this service.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.contracts.forms import FieldCondition, FieldType, FormDefinition, FormField
from app.core.config import get_settings


class Condition(BaseModel):
    """A field is only relevant when the condition holds. `proxy`: actor acts for somebody else (Vertretung)."""
    model_config = ConfigDict(extra="forbid")
    field: str | None = None
    equals: str | bool | None = None
    one_of: list[str] = []
    proxy: bool | None = None

    @model_validator(mode="after")
    def _one_kind(self):
        if (self.field is None) == (self.proxy is None):
            raise ValueError("condition needs exactly one of 'field' or 'proxy'")
        return self


class FieldSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    label_de: str
    type: FieldType
    section: str
    required: bool = False
    recommended: bool = Field(False, description="Not required by the form, but worth asking (next-questions?include_optional)")
    ask_hint_de: str = ""
    options: list[str] = []
    pdf_field: str | None = Field(None, description="AcroForm field name; defaults to id; null for unmapped virtual fields")
    pdf_on_value: str | None = Field(None, description="checkbox: export value when ticked, e.g. '/ja'")
    pdf_options: dict[str, str] = Field({}, description="choice: option label -> export value of the radio kid")
    pdf_overflow: list[str] = Field([], description="continuation lines for long text (filled in order)")
    max_chars: int | None = Field(None, description="characters per line before continuing in pdf_overflow")
    compact: bool = Field(False, description="strip whitespace + uppercase on input (comb fields: IBAN, SVNR)")
    when: Condition | None = None
    prefill: str | None = Field(None, description="profile.<key> | actor.<key> | delegation.<key> | document.<key> | "
                                                   "system.<key> | const:<value>")
    doctor_only: bool = False
    readonly_reason_de: str | None = None

    @model_validator(mode="after")
    def _consistent(self):
        if self.type == FieldType.choice:
            if not self.options:
                raise ValueError(f"{self.id}: choice needs options")
            if self.pdf_target and set(self.pdf_options) != set(self.options):
                raise ValueError(f"{self.id}: pdf_options must map every option")
        if self.type == FieldType.checkbox and self.pdf_target and not self.pdf_on_value:
            raise ValueError(f"{self.id}: checkbox needs pdf_on_value")
        if self.doctor_only and (self.required or self.prefill):
            raise ValueError(f"{self.id}: doctor_only fields are never required or prefilled")
        if self.doctor_only and not self.readonly_reason_de:
            raise ValueError(f"{self.id}: doctor_only needs readonly_reason_de")
        return self

    @property
    def pdf_target(self) -> str | None:
        return self.pdf_field if "pdf_field" in self.model_fields_set else self.id

    @property
    def readonly(self) -> bool:
        return self.doctor_only or self.readonly_reason_de is not None

    def to_contract(self) -> FormField:
        return FormField(id=self.id, label_de=self.label_de, type=self.type, section=self.section,
                         required=self.required, ask_hint_de=self.ask_hint_de, options=self.options,
                         readonly_reason_de=self.readonly_reason_de,
                         when=FieldCondition(**self.when.model_dump()) if self.when else None)


class FormSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    form_id: str
    title_de: str
    provider: str
    form_version: str = Field(..., description="Version printed on the official form, e.g. 'PAL 080 (01. 2025)'")
    submit_info_de: str
    sections: list[str]
    doctor_only_pages: list[int] = Field([], description="1-based pages filled only by doctors; never written")
    unmapped_pdf_fields: dict[str, str] = Field({}, description="AcroForm fields deliberately not mapped -> reason")
    stamp: Literal["top", "bottom"] = "top"
    fields: list[FieldSpec]

    @model_validator(mode="after")
    def _refs(self):
        ids = [f.id for f in self.fields]
        if len(ids) != len(set(ids)):
            raise ValueError(f"{self.form_id}: duplicate field ids")
        for f in self.fields:
            if f.section not in self.sections:
                raise ValueError(f"{self.form_id}.{f.id}: unknown section {f.section!r}")
            if f.when and f.when.field and f.when.field not in ids:
                raise ValueError(f"{self.form_id}.{f.id}: condition refers to unknown field {f.when.field!r}")
        return self

    def field(self, field_id: str) -> FieldSpec | None:
        return next((f for f in self.fields if f.id == field_id), None)

    def to_contract(self) -> FormDefinition:
        return FormDefinition(form_id=self.form_id, title_de=self.title_de, provider=self.provider,
                              sections=self.sections, fields=[f.to_contract() for f in self.fields],
                              submit_info_de=self.submit_info_de)


def forms_dir() -> Path:
    return get_settings().knowledge_dir / "forms"


def template_pdf(form_id: str) -> Path:
    return forms_dir() / "templates" / f"{form_id}.pdf"


@lru_cache
def load_specs() -> dict[str, FormSpec]:
    specs = {}
    for p in sorted(forms_dir().glob("*.yaml")):
        spec = FormSpec(**yaml.safe_load(p.read_text(encoding="utf-8")))
        specs[spec.form_id] = spec
    return specs


def get_spec(form_id: str) -> FormSpec | None:
    return load_specs().get(form_id)


def json_schema() -> dict:
    schema = FormSpec.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "SV KI-Lotse form schema (knowledge/forms/<form_id>.yaml)"
    return schema


if __name__ == "__main__":  # regenerate knowledge/schema/form.schema.json
    out = get_settings().knowledge_dir / "schema" / "form.schema.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(json_schema(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(out)
