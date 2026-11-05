"""benefits — catalog (knowledge/benefits.yaml) + deterministic eligibility. REAL (owner: WS-B)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.contracts.benefits import Benefit, Bundle, BundleRequest, EligibilityRequest, EligibilityResult
from app.contracts.documents import DocumentAnalysis, Recommendation
from app.contracts.identity import Person, Scope
from app.core.auth import Context, require
from app.core.db import store
from app.fixtures import ANNA_ANALYSIS
from app.seed.loader import delegations_of_grantee, get_person
from app.services.benefits import bundles, catalog
from app.services.benefits.service import DocRec, EvalInput, evaluate
from app.services.prevention.engine import evaluate as prevention_evaluate
from app.services.prevention.router import _stored_vaccinations as stored_vaccinations

router = APIRouter(prefix="/api/benefits", tags=["benefits"])

ANALYSES = "document_analyses"   # owned by WS-D: key = document_id, value = DocumentAnalysis.model_dump()


def _analyses(ctx: Context, document_ids: list[str]) -> list[DocumentAnalysis]:
    if not document_ids:
        return []
    if Scope.read_documents not in ctx.scopes:
        raise HTTPException(403, f"Fehlende Berechtigung 'read_documents' für {ctx.subject.first_name} "
                                 f"{ctx.subject.last_name}.")
    own = {a["document_id"]: a for a in store.list(ANALYSES, subject_id=ctx.subject.id)}
    out = []
    for did in document_ids:
        if did in own:
            out.append(DocumentAnalysis.model_validate(own[did]))
        elif did == ANNA_ANALYSIS.document_id and ctx.subject.id == "anna":
            out.append(ANNA_ANALYSIS)          # golden fallback until the document has been analysed
        else:
            ctx.rule_ids.append(f"benefits.document_skipped:{did}")  # not analysed (yet): skip, visible in audit
    return out


def _children(subject: Person) -> list[Person]:
    kids = []
    for d in delegations_of_grantee(subject.id):
        if "obsorge" in d.relation.lower():
            p = get_person(d.grantor_id)
            if p:
                kids.append(p)
    return kids


def build_input(ctx: Context, req: EligibilityRequest) -> EvalInput:
    facts = dict(req.facts or {})
    recs: list[DocRec] = []
    living = None
    for a in _analyses(ctx, req.document_ids):
        recs += [DocRec(r, a.filename, a.document_id) for r in a.recommendations]
        living = living or a.person.living_situation
    # Lebenslage: facts from CONFIRMED episodes (only with the Lebenslage scope); explicit request facts win.
    # Known facts answered earlier (cockpit or Lotsi) – request facts win.
    known = known_facts(ctx.subject.id)["facts"]
    if known:
        facts = {**known, **facts}
        ctx.rule_ids.append("benefits.facts_known:" + ",".join(sorted(known)))
    if Scope.manage_situation in ctx.scopes:
        from app.services.situation.service import situation_facts

        sit = situation_facts(ctx.subject.id)
        if sit:
            facts = {**sit, **facts}
            ctx.rule_ids.append("benefits.facts_from_situation:" + ",".join(sorted(sit)))
    for r in facts.pop("recommendations", None) or []:
        recs.append(DocRec(Recommendation.model_validate(r), str(facts.get("document_filename", "Dokument"))))
    as_of = date.today()
    if facts.get("as_of"):
        try:
            as_of = date.fromisoformat(str(facts["as_of"]))
        except ValueError as exc:
            raise HTTPException(422, "facts.as_of muss ein ISO-Datum sein (JJJJ-MM-TT).") from exc
    return EvalInput(subject=ctx.subject, facts=facts, recs=recs, children=_children(ctx.subject), as_of=as_of,
                     living_situation=living)


def _audit(ctx: Context, results: list[EligibilityResult]) -> None:
    for res in results:
        ctx.rule_ids.extend(res.rule_ids)
        ctx.cite(*{c.source.label for c in res.criteria if c.source})


@router.get("", response_model=list[Benefit], summary="Benefit catalog (benefits and offers)")
def list_catalog(area: str | None = None,
                 kind: str | None = Query(None, pattern="^(benefit|offer)$",
                                          description="benefit = Leistung, offer = Angebot (ids 'angebot_*')"),
                 ctx: Context = Depends(require())):
    return [b for b in catalog.benefits(kind) if area is None or b.area == area]


@router.get("/rezeptgebuehr/check", response_model=list[EligibilityResult],
            summary="Rezeptgebühr calculator: befreit / Obergrenze 2 % / nicht befreit")
def rezeptgebuehr_check(net_income_monthly: float = Query(..., ge=0),
                        household: str = Query("alleinstehend", pattern="^(alleinstehend|paar)$"),
                        children_count: int = Query(0, ge=0), chronic_illness_expenses: bool | None = None,
                        receives_ausgleichszulage: bool | None = None, ctx: Context = Depends(require())):
    facts = {"net_income_monthly": net_income_monthly, "household": household, "children_count": children_count,
             "chronic_illness_expenses": chronic_illness_expenses,
             "receives_ausgleichszulage": receives_ausgleichszulage}
    inp = EvalInput(subject=ctx.subject, facts=facts)
    res = evaluate(inp, ["rezeptgebuehrenbefreiung", "rezeptgebuehrenobergrenze"])
    _audit(ctx, res)
    return res


@router.get("/{benefit_id}", response_model=Benefit, summary="One benefit incl. legal basis and sources")
def get_benefit(benefit_id: str, ctx: Context = Depends(require())):
    e = catalog.get(benefit_id)
    if e is None:
        raise HTTPException(404, "Leistung nicht gefunden")
    ctx.cite(*(s.label for s in e.benefit.legal_basis))
    return e.benefit


@router.post("/eligibility", response_model=list[EligibilityResult], summary="Deterministic eligibility check")
def eligibility(req: EligibilityRequest, ctx: Context = Depends(require())):
    if req.subject_id and req.subject_id != ctx.subject.id:
        raise HTTPException(403, "subject_id passt nicht zur Person, für die Sie gerade handeln (X-Subject-Id).")
    unknown = [b for b in (req.benefit_ids or []) if catalog.get(b) is None]
    if unknown:
        raise HTTPException(404, f"Unbekannte Leistung(en): {', '.join(unknown)}")
    res = evaluate(build_input(ctx, req), req.benefit_ids)
    _audit(ctx, res)
    return res



# ---- Situation bundles ("Bündel") — owner: WS-K2 ----------------------------------------------------------------


def _bundle_context(ctx: Context, facts: dict, document_ids: list[str]) -> bundles.BundleContext:
    inp = build_input(ctx, EligibilityRequest(subject_id=ctx.subject.id, facts=facts, document_ids=document_ids))
    see = Scope.view_health_prevention in ctx.scopes
    items = []
    if see:
        vaccinations, _ = stored_vaccinations(ctx.subject.id)
        fh = inp.facts.get("family_history")
        fh = [fh] if isinstance(fh, str) else fh if isinstance(fh, list) else None
        items, rules = prevention_evaluate(ctx.subject, vaccinations, inp.as_of, fh)
        ctx.rule_ids.extend(r for r in rules if r.startswith("prevention.family_history."))
    return bundles.BundleContext(inp=inp, can_see_prevention=see, prevention_items=items)


def _finish(ctx: Context, bc: bundles.BundleContext, b: Bundle) -> Bundle:
    ctx.rule_ids.extend(bc.rule_ids)
    ctx.cite(*{i.source.label for i in b.items if i.source})
    return b


@router.get("/bundles/catalog", response_model=list[Bundle],
            summary="All situation bundles (Pflege, nach dem Spital, …), evaluated for the current person")
def bundle_catalog(ctx: Context = Depends(require())):
    out = []
    for bid in bundles.specs():
        bc = _bundle_context(ctx, {}, [])
        out.append(_finish(ctx, bc, bundles.build(bid, bc)))
    return out


@router.post("/bundles/match", response_model=Bundle | None,
             summary="Bundle for a situation (id or free text) + facts; null if the text matches no situation")
def bundle_match(body: BundleRequest, ctx: Context = Depends(require())):
    if body.situation:
        if body.situation not in bundles.specs():
            raise HTTPException(404, f"Unbekannte Situation: {body.situation}. Möglich: {', '.join(bundles.specs())}.")
        bid = body.situation
        ctx.rule_ids.append(f"bundles.match.explicit:{bid}")
    elif body.text and body.text.strip():
        m = bundles.match_text(body.text)
        if m is None and not body.document_ids:
            ctx.rule_ids.append("bundles.match.none")
            return None
        bid = m.bundle_id if m else "nach_spital"
        ctx.rule_ids.append(f"bundles.match.text:{bid}:{','.join(m.hits) if m else 'document'}")
    elif body.document_ids:
        bid = "nach_spital"                     # a document without a question -> "what do I do now?"
        ctx.rule_ids.append("bundles.match.document:nach_spital")
    else:
        raise HTTPException(422, "Bitte eine Situation (situation) oder eine Beschreibung (text) angeben.")
    bc = _bundle_context(ctx, body.facts, body.document_ids)
    return _finish(ctx, bc, bundles.build(bid, bc))


# ---- Known facts (answers to open questions), shared by cockpit and Lotsi ---------------------------------------
FACTS_COLL = "known_facts"
_NOT_STORED = {"recommendations", "as_of", "document_filename"}


def known_facts(subject_id: str) -> dict:
    return store.get(FACTS_COLL, subject_id) or {"facts": {}, "sources": {}}


@router.get("/facts", summary="Answers given so far for the subject (shared by cockpit and Lotsi), with provenance")
def get_facts(ctx: Context = Depends(require())):
    return known_facts(ctx.subject.id)


@router.patch("/facts", summary="Store answers (merge; value null deletes). Provenance: who, when, via cockpit/Lotsi")
def patch_facts(body: dict, ctx: Context = Depends(require())):
    from app.core.db import now_iso

    data = known_facts(ctx.subject.id)
    via = "Lotsi" if ctx.via == "agent" else "Cockpit"
    changed = []
    for k, v in (body.get("facts") or {}).items():
        if k in _NOT_STORED:
            continue
        if v is None:
            data["facts"].pop(k, None)
            data["sources"].pop(k, None)
        else:
            data["facts"][k] = v
            data["sources"][k] = {"label": f"Angabe von {ctx.actor.first_name} {ctx.actor.last_name}, "
                                           f"{now_iso()[8:10]}.{now_iso()[5:7]}.{now_iso()[:4]} ({via})"}
        changed.append(k)
    store.put(FACTS_COLL, ctx.subject.id, data, subject_id=ctx.subject.id)
    ctx.rule_ids.append("benefits.facts_saved:" + ",".join(sorted(changed)))
    return data


# '/facts' must win over the generic '/{benefit_id}' route registered earlier.
for _r in [r for r in router.routes if getattr(r, "path", "").endswith("/facts")]:
    router.routes.remove(_r)
    router.routes.insert(0, _r)
