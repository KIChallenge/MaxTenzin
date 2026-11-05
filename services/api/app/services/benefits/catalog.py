"""Benefit catalog: loads knowledge/benefits.yaml, validates it and resolves every source spec to a SourceRef.

Resolution is strict: an unknown paragraph, page, form or value raises at load time (covered by tests), so a
benefit can never be shown with a dangling citation.
"""

from __future__ import annotations

import json
from functools import lru_cache

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.contracts.benefits import Benefit
from app.contracts.common import SourceKind, SourceRef
from app.core.knowledge import jsonl, kpath, yaml_file
from app.services.legal import service as legal
from app.services.values import service as values

BROCHURE = "ÖGK Serviceratgeber 2026"
FORM_LABELS = {
    "pva_pflegegeld_pal080": "PAL 080",
    "fsw_foerderung": "FSW Antrag auf Förderung von Leistungen",
    "oegk_fahrtkosten_wien": "ÖGK Antrag auf Zuschuss zu Fahrtkosten",
    "sv_kur_reha": "Antrag auf Rehabilitations-, Kur- bzw. Erholungsaufenthalt",
}


class SourceSpec(BaseModel):
    """Exactly one of law / page / form / value."""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    law: str | None = None
    nr: str | None = None
    abs_: str | None = Field(None, alias="abs")
    page: int | None = None
    form: str | None = None
    label: str | None = None
    value: str | None = None

    @model_validator(mode="after")
    def _one_kind(self):
        kinds = [self.law is not None, self.form is not None, self.value is not None,
                 self.page is not None and self.form is None]
        if sum(kinds) != 1:
            raise ValueError(f"source spec needs exactly one of law/page/form/value: {self}")
        if self.law is not None and not self.nr:
            raise ValueError("law source needs nr")
        return self


class CriterionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label_de: str
    source: SourceSpec


class BenefitSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name_de: str
    area: str = Field(pattern="^[A-F]$")
    provider: str
    summary_de: str
    plain_de: str
    form_ids: list[str] = []
    required_documents_de: list[str] = []
    legal_basis: list[SourceSpec] = []
    sources: list[SourceSpec] = []
    value_refs: list[str] = []
    criteria: dict[str, CriterionSpec]


class CatalogFile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int
    areas: dict[str, str]
    benefits: list[BenefitSpec]


@lru_cache
def _pages() -> set[int]:
    return {r["printed_page"] for r in jsonl("extracted/serviceratgeber/pages.jsonl")}


@lru_cache
def _form_pages(form_id: str) -> int:
    p = kpath("forms", "templates", f"{form_id}.fields.json")
    if not p.exists():
        raise KeyError(f"form template {form_id} missing")
    return json.loads(p.read_text(encoding="utf-8"))["pages"]


def brochure_ref(page: int) -> SourceRef:
    if page not in _pages():
        raise KeyError(f"Serviceratgeber page {page} missing")
    return SourceRef(kind=SourceKind.brochure, label=f"{BROCHURE}, S. {page}", ref=f"page:{page}")


def resolve(s: SourceSpec) -> SourceRef:
    if s.law is not None:
        return legal.source_ref(s.law, s.nr or "", s.abs_)
    if s.value is not None:
        return values.require_value(s.value).source
    if s.form is not None:
        n = _form_pages(s.form)
        page = s.page or 1
        if not 1 <= page <= n:
            raise KeyError(f"form {s.form} has no page {page}")
        label = s.label or f"{FORM_LABELS.get(s.form, s.form)}, S. {page}"
        return SourceRef(kind=SourceKind.form, label=label, ref=f"{s.form}#page={page}")
    return brochure_ref(s.page or 0)


class CatalogEntry:
    """Resolved benefit: contract model + resolved criteria sources + value refs."""

    def __init__(self, spec: BenefitSpec):
        self.spec = spec
        self.benefit = Benefit(
            id=spec.id, name_de=spec.name_de, area=spec.area, summary_de=spec.summary_de, plain_de=spec.plain_de,
            provider=spec.provider, form_ids=spec.form_ids, required_documents_de=spec.required_documents_de,
            legal_basis=[resolve(s) for s in spec.legal_basis], sources=[resolve(s) for s in spec.sources],
        )
        self.criteria: dict[str, tuple[str, SourceRef]] = {
            cid: (c.label_de, resolve(c.source)) for cid, c in spec.criteria.items()
        }
        for key in spec.value_refs:
            values.require_value(key)


@lru_cache
def catalog_file() -> CatalogFile:
    raw = yaml_file("benefits.yaml")
    if raw is None:
        raise FileNotFoundError("knowledge/benefits.yaml missing")
    return CatalogFile.model_validate(raw)


@lru_cache
def entries() -> dict[str, CatalogEntry]:
    out: dict[str, CatalogEntry] = {}
    for spec in catalog_file().benefits:
        if spec.id in out:
            raise ValueError(f"duplicate benefit id {spec.id}")
        out[spec.id] = CatalogEntry(spec)
    return out


def benefits() -> list[Benefit]:
    return [e.benefit for e in entries().values()]


def get(benefit_id: str) -> CatalogEntry | None:
    return entries().get(benefit_id)


def json_schema() -> dict:
    schema = CatalogFile.model_json_schema(by_alias=True)
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "SV KI-Lotse benefit catalog (knowledge/benefits.yaml)"
    return schema
