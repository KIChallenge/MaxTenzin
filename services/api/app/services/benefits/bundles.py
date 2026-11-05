"""Situation bundles ("Bündel") — knowledge/bundles.yaml + deterministic matching + assembly (no LLM). Owner: WS-K2.

A bundle lists everything relevant for a life situation in a curated order. Benefit/offer items carry the status of the
real eligibility engine (same facts, same document recommendations), prevention items come from the prevention engine
(only with scope view_health_prevention), offices from the directory. Load-time validation: every ref must exist and
every source must resolve (covered by tests), so a bundle can never point to an unknown benefit or a dangling citation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.contracts.benefits import Bundle, BundleItem, EligibilityResult, EligibilityStatus
from app.contracts.common import SourceKind, SourceRef
from app.contracts.prevention import PreventionItem, PreventionStatus
from app.core.knowledge import kpath, yaml_file
from app.services.benefits import catalog
from app.services.benefits.catalog import SourceSpec
from app.services.benefits.service import EvalInput, evaluate
from app.services.directory import service as directory
from app.services.prevention import engine as prevention

RULE_VERSION = "v1"
FAMILY_MARK = "Besonders relevant"           # prefix set by the prevention engine for family-history matches
STRONG, WEAK = 3, 1
MAX_QUESTIONS = 3


class ItemSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["benefit", "prevention", "appointment", "office", "form"]
    ref: str
    why_de: str
    title_de: str | None = None
    source: SourceSpec | None = None
    if_fact: str | None = None
    if_benefit: str | None = None
    with_prevention: str | None = None   # benefit item: append that prevention item's family-history explanation

    @model_validator(mode="after")
    def _appointment(self):
        if self.kind == "appointment" and (not self.title_de or self.source is None):
            raise ValueError(f"appointment item {self.ref} needs title_de and source")
        return self


class MatchSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strong: list[str] = Field(min_length=1)
    weak: list[str] = []


class BundleSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    title_de: str
    situation_de: str
    match: MatchSpec
    questions: list[str] = []
    next_step_de: str
    items: list[ItemSpec] = Field(min_length=1)


class BundlesFile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int
    questions: dict[str, str]
    bundles: list[BundleSpec]


# --------------------------------------------------------------------------------------------- loading + validation


def _prevention_ids() -> set[str]:
    return {r["id"] for r in prevention.knowledge()["rules"]}


@lru_cache
def bundles_file() -> BundlesFile:
    raw = yaml_file("bundles.yaml")
    if raw is None:
        raise FileNotFoundError("knowledge/bundles.yaml missing")
    f = BundlesFile.model_validate(raw)
    _validate(f)
    return f


def _validate(f: BundlesFile) -> None:
    seen: set[str] = set()
    for b in f.bundles:
        if b.id in seen:
            raise ValueError(f"duplicate bundle id {b.id}")
        seen.add(b.id)
        for q in b.questions:
            if q not in f.questions:
                raise ValueError(f"bundle {b.id}: no question text for fact {q}")
        for it in b.items:
            if it.kind == "benefit" and catalog.get(it.ref) is None:
                raise ValueError(f"bundle {b.id}: unknown benefit/offer {it.ref}")
            if it.if_benefit and catalog.get(it.if_benefit) is None:
                raise ValueError(f"bundle {b.id}: unknown if_benefit {it.if_benefit}")
            for pid in (it.ref if it.kind == "prevention" else None, it.with_prevention):
                if pid and pid not in _prevention_ids():
                    raise ValueError(f"bundle {b.id}: unknown prevention rule {pid}")
            if it.kind == "form" and not kpath("forms", f"{it.ref}.yaml").exists():
                raise ValueError(f"bundle {b.id}: unknown form {it.ref}")
            if it.kind == "office" and not directory.search(topic=it.ref):
                raise ValueError(f"bundle {b.id}: no office for topic {it.ref}")
            if it.source is not None:
                catalog.resolve(it.source)        # raises on a dangling citation


def specs() -> dict[str, BundleSpec]:
    return {b.id: b for b in bundles_file().bundles}


# --------------------------------------------------------------------------------------------- matching


_NON_WORD = re.compile(r"[^a-z0-9]+")


def fold(text: str) -> str:
    """Lower-case, fold umlauts, strip punctuation; padded with spaces for word-start matching."""
    t = text.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        t = t.replace(a, b)
    return " " + " ".join(_NON_WORD.sub(" ", t).split()) + " "


@dataclass
class Match:
    bundle_id: str
    score: int
    hits: list[str] = field(default_factory=list)


def match_text(text: str) -> Match | None:
    """Deterministic keyword scoring. Highest score wins, ties by file order; no hit -> None."""
    t = fold(text)
    best: Match | None = None
    for b in bundles_file().bundles:
        m = Match(b.id, 0)
        for kws, w in ((b.match.strong, STRONG), (b.match.weak, WEAK)):
            for kw in kws:
                if fold(kw).rstrip() in t:
                    m.score += w
                    m.hits.append(kw)
        if m.score and (best is None or m.score > best.score):
            best = m
    return best


# --------------------------------------------------------------------------------------------- assembly


@dataclass
class BundleContext:
    inp: EvalInput
    can_see_prevention: bool
    prevention_items: list[PreventionItem] = field(default_factory=list)
    rule_ids: list[str] = field(default_factory=list)
    results: list[EligibilityResult] = field(default_factory=list)


def _true(v) -> bool:
    return v is True or (isinstance(v, str) and v.lower() in ("true", "ja", "yes"))


def _result_source(res: EligibilityResult) -> tuple[SourceRef | None, str]:
    """Prefer an explicit document recommendation (quote + page), else the legal basis, else the first source."""
    doc = next((c for c in res.criteria if c.source and c.source.kind == SourceKind.document), None)
    if doc and doc.source:
        return doc.source, f" Im Dokument ausdrücklich empfohlen ({doc.source.label})."
    b = res.benefit
    src = (b.legal_basis or b.sources or [None])[0] or next((c.source for c in res.criteria if c.source), None)
    return src, ""


def _benefit_item(it: ItemSpec, bc: BundleContext, cache: dict[str, EligibilityResult]) -> BundleItem | None:
    res = cache.get(it.ref) or evaluate(bc.inp, [it.ref])[0]
    cache[it.ref] = res
    if res.status == EligibilityStatus.not_applicable:
        return None
    bc.results.append(res)
    src, doc_note = _result_source(res)
    if it.with_prevention and bc.can_see_prevention:
        p = next((i for i in bc.prevention_items if i.id == it.with_prevention), None)
        if p is not None and p.explanation_de.startswith(FAMILY_MARK):
            doc_note += " " + p.explanation_de
            src = next((s for s in reversed(p.sources) if s.kind == SourceKind.brochure), src)
    kind = "offer" if catalog.is_offer(it.ref) else "benefit"
    return BundleItem(kind=kind, ref_id=it.ref, title_de=res.benefit.name_de, why_de=it.why_de + doc_note,
                      status=res.status, status_de=_status_de(kind, it.ref, res.status),
                      source=catalog.resolve(it.source) if it.source else src)


OPEN_TO_ALL = {"vorsorgeuntersuchung"}  # free services without a decision by a Träger
STATUS_DE = {"likely": "kommt voraussichtlich in Frage", "possible": "kommt möglicherweise in Frage",
             "needs_info": "noch Angaben nötig", "not_applicable": "trifft nicht zu"}
PREVENTION_STATUS_DE = {"due": "jetzt fällig", "upcoming": "demnächst", "up_to_date": "aktuell",
                        "not_documented": "nicht im e-Impfpass dokumentiert – mit Ärztin bzw. Arzt klären"}


def _status_de(kind: str, ref: str, status) -> str | None:
    st = getattr(status, "value", status)
    if (kind == "offer" or ref in OPEN_TO_ALL) and st == "likely":
        return "kostenlos nutzbar"
    return STATUS_DE.get(st)


def _prevention_item(it: ItemSpec, bc: BundleContext) -> BundleItem | None:
    if not bc.can_see_prevention:
        if "bundles.prevention_skipped_no_scope" not in bc.rule_ids:
            bc.rule_ids.append("bundles.prevention_skipped_no_scope")
        return None
    p = next((i for i in bc.prevention_items if i.id == it.ref), None)
    if p is None or (p.status == PreventionStatus.up_to_date and not p.explanation_de.startswith(FAMILY_MARK)):
        return None
    return BundleItem(kind="prevention", ref_id=p.id, title_de=p.title_de, why_de=f"{it.why_de} {p.explanation_de}",
                      status_de=PREVENTION_STATUS_DE.get(getattr(p.status, "value", p.status)),
                      source=p.sources[0] if p.sources else None)


def _office_item(it: ItemSpec, bc: BundleContext) -> BundleItem | None:
    offs = directory.search(topic=it.ref, zip_=bc.inp.subject.address.zip, limit=1)
    if not offs:
        return None
    o = offs[0]
    where = ", ".join(x for x in (o.address, f"{o.zip} {o.city}".strip()) if x)
    tel = f", Tel. {o.phone}" if o.phone else ""
    return BundleItem(kind="office", ref_id=o.id, title_de=f"Zuständig: {o.name} ({where}{tel})", why_de=it.why_de,
                      source=o.source)


def _form_item(it: ItemSpec) -> BundleItem:
    spec = yaml_file(f"forms/{it.ref}.yaml") or {}
    title = spec.get("title_de") or catalog.FORM_LABELS.get(it.ref, it.ref)
    src = catalog.resolve(it.source) if it.source else catalog.resolve(SourceSpec(form=it.ref, page=1))
    return BundleItem(kind="form", ref_id=it.ref, title_de=f"Formular: {title}", why_de=it.why_de, source=src)


def _questions(b: BundleSpec, missing: list[str]) -> list[str]:
    texts = bundles_file().questions
    order = {f: i for i, f in enumerate(b.questions)}
    ranked = sorted(dict.fromkeys(m for m in missing if m in texts), key=lambda f: (order.get(f, len(order)),))
    return [texts[f] for f in ranked[:MAX_QUESTIONS]]


def build(bundle_id: str, bc: BundleContext) -> Bundle:
    b = specs()[bundle_id]
    facts = bc.inp.facts
    cache: dict[str, EligibilityResult] = {}
    items: list[BundleItem] = []
    missing: list[str] = []
    for it in b.items:
        if it.if_fact and not _true(facts.get(it.if_fact)):
            continue
        if it.if_benefit:
            dep = cache.get(it.if_benefit) or evaluate(bc.inp, [it.if_benefit])[0]
            cache[it.if_benefit] = dep
            if dep.status == EligibilityStatus.not_applicable:
                continue
        if it.kind == "benefit":
            item = _benefit_item(it, bc, cache)
            if item is not None:
                missing += cache[it.ref].missing_fields
        elif it.kind == "prevention":
            item = _prevention_item(it, bc)
            if item is not None and "family_history" not in facts:
                missing.append("family_history")
        elif it.kind == "office":
            item = _office_item(it, bc)
        elif it.kind == "form":
            item = _form_item(it)
        else:  # appointment
            item = BundleItem(kind="appointment", ref_id=it.ref, title_de=it.title_de or it.ref, why_de=it.why_de,
                              source=catalog.resolve(it.source) if it.source else None)
        if item is not None:
            items.append(item)
    bc.rule_ids.append(f"bundles.{b.id}.{RULE_VERSION}")
    for r in bc.results:
        bc.rule_ids.extend(r.rule_ids)
    return Bundle(id=b.id, title_de=b.title_de, situation_de=b.situation_de, items=items,
                  questions_de=_questions(b, missing), next_step_de=b.next_step_de)
