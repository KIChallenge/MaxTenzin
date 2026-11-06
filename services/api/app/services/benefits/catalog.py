"""Benefit catalog: loads knowledge/benefits.yaml, validates it and resolves every source spec to a SourceRef.

Resolution is strict: an unknown paragraph, page, form or value raises at load time (covered by tests), so a
benefit can never be shown with a dangling citation.
"""

from __future__ import annotations

import json
import re
from datetime import date
from functools import lru_cache
from typing import Literal

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
    "oegk_rezeptgebuehr_befreiung": "ÖGK Antrag auf Befreiung von der Rezeptgebühr",
}


class SourceSpec(BaseModel):
    """Exactly one of law / page / form / value / url (external website with label + retrieval date)."""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    law: str | None = None
    nr: str | None = None
    abs_: str | None = Field(None, alias="abs")
    page: int | None = None
    quote: str | None = None          # brochure page: verbatim quote, checked against the page text at load time
    form: str | None = None
    label: str | None = None
    value: str | None = None
    url: str | None = None            # external official website (outside the provided data)
    retrieved: str | None = None      # ISO date the external page was checked

    @model_validator(mode="after")
    def _one_kind(self):
        kinds = [self.law is not None, self.form is not None, self.value is not None, self.url is not None,
                 self.page is not None and self.form is None]
        if sum(kinds) != 1:
            raise ValueError(f"source spec needs exactly one of law/page/form/value/url: {self}")
        if self.law is not None and not self.nr:
            raise ValueError("law source needs nr")
        if self.url is not None:
            if not self.url.startswith("https://") or not self.label or not self.retrieved:
                raise ValueError(f"external source needs https url, label and retrieved date: {self}")
            date.fromisoformat(self.retrieved)
        if self.quote is not None and (self.page is None or self.form is not None):
            raise ValueError("quote is only allowed on brochure page sources")
        return self


class CriterionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label_de: str
    source: SourceSpec


class OfferSpec(BaseModel):
    """Extra rules for offers (kind: offer) — open programmes, evaluated by the generic offer evaluator."""
    model_config = ConfigDict(extra="forbid")
    min_age: int | None = None
    max_age: int | None = None
    audience: Literal["insured", "employer", "school", "club"] = "insured"
    requires_fact: str | None = None  # fact that must be true (young_child is derived from the children in Obsorge)
    season_months: list[int] = []     # e.g. [6, 7, 8, 9] for summer programmes
    steps_de: list[str] = Field(min_length=1)
    cost_de: str


class BenefitSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    kind: Literal["benefit", "offer"] = "benefit"
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
    offer: OfferSpec | None = None

    @model_validator(mode="after")
    def _offer_rules(self):
        if (self.kind == "offer") != (self.offer is not None):
            raise ValueError(f"{self.id}: 'offer' rules are required for kind offer and only allowed there")
        if self.kind == "offer" and not self.id.startswith("angebot_"):
            raise ValueError(f"{self.id}: offer ids start with 'angebot_'")
        return self


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


_WS = re.compile(r"\s+")


def norm_text(text: str) -> str:
    """Whitespace-normalised text for verbatim quote checks (soft hyphen / nbsp unified)."""
    return _WS.sub(" ", text.replace("­", "").replace(" ", " ")).strip()


@lru_cache
def _page_texts() -> dict[int, str]:
    out: dict[int, str] = {}
    for r in jsonl("extracted/serviceratgeber/pages.jsonl"):
        out[r["printed_page"]] = out.get(r["printed_page"], "") + "\n" + r["text"]
    return {k: norm_text(v) for k, v in out.items()}


def brochure_ref(page: int, quote: str | None = None) -> SourceRef:
    if page not in _pages():
        raise KeyError(f"Serviceratgeber page {page} missing")
    if quote is not None and norm_text(quote) not in _page_texts()[page]:
        raise KeyError(f"quote not found verbatim on Serviceratgeber page {page}: {quote!r}")
    return SourceRef(kind=SourceKind.brochure, label=f"{BROCHURE}, S. {page}", ref=f"page:{page}", quote=quote)


def external_ref(label: str, url: str, retrieved: str) -> SourceRef:
    d = date.fromisoformat(retrieved)
    return SourceRef(kind=SourceKind.external, label=f"{label} (externe Quelle, abgerufen am {d:%d.%m.%Y})",
                     ref=url, retrieved=retrieved)


def resolve(s: SourceSpec) -> SourceRef:
    if s.url is not None:
        return external_ref(s.label or "", s.url, s.retrieved or "")
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
    return brochure_ref(s.page or 0, s.quote)


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


def benefits(kind: str | None = None) -> list[Benefit]:
    return [e.benefit for e in entries().values() if kind is None or e.spec.kind == kind]


def is_offer(benefit_id: str) -> bool:
    e = entries().get(benefit_id)
    return e is not None and e.spec.kind == "offer"


def get(benefit_id: str) -> CatalogEntry | None:
    return entries().get(benefit_id)


def json_schema() -> dict:
    schema = CatalogFile.model_json_schema(by_alias=True)
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "SV KI-Lotse benefit catalog (knowledge/benefits.yaml)"
    return schema
