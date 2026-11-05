"""benefits — catalog (knowledge/benefits.yaml) + deterministic eligibility. REAL (owner: WS-B)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.contracts.benefits import Benefit, EligibilityRequest, EligibilityResult
from app.contracts.documents import DocumentAnalysis, Recommendation
from app.contracts.identity import Person, Scope
from app.core.auth import Context, require
from app.core.db import store
from app.fixtures import ANNA_ANALYSIS
from app.seed.loader import delegations_of_grantee, get_person
from app.services.benefits import catalog
from app.services.benefits.service import DocRec, EvalInput, evaluate

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
        recs += [DocRec(r, a.filename) for r in a.recommendations]
        living = living or a.person.living_situation
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


@router.get("", response_model=list[Benefit], summary="Benefit catalog")
def list_catalog(area: str | None = None, ctx: Context = Depends(require())):
    return [b for b in catalog.benefits() if area is None or b.area == area]


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
