"""legal — Rechtsgrundlagen from the SozDok corpus: exact lookup + SQLite FTS5/BM25 search. (owner: WS-B)."""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.contracts.misc import LawParagraphEntry, LegalHit, LegalParagraph
from app.core.auth import Context, require
from app.services.legal import fts, service

router = APIRouter(prefix="/api/legal", tags=["legal"])


@router.get("/paragraphs/{law_key}/{nr}", response_model=LegalParagraph, summary="Exact paragraph, e.g. BPGG / 4")
def paragraph(law_key: str, nr: str, ctx: Context = Depends(require())):
    r = service.find(law_key, nr)
    if r is None:
        raise HTTPException(404, "Paragraph nicht gefunden")
    p = service.to_paragraph(r)
    ctx.cite(p.citation_de)
    return p


@router.get("/search", response_model=list[LegalHit], summary="Full-text search (SQLite FTS5, BM25, core-law boost)")
def search(q: str, law: str | None = None, limit: int = Query(10, ge=1, le=50), ctx: Context = Depends(require())):
    hits = [LegalHit(paragraph=service.to_paragraph(r), score=s, snippet=snip) for r, s, snip in fts.search(q, law, limit)]
    ctx.cite(*(h.paragraph.citation_de for h in hits[:3]))
    return hits


@router.get("/laws", summary="All laws/guidelines in the corpus: key, abbreviation, title, paragraph count")
def laws(ctx: Context = Depends(require())):
    from app.core.knowledge import jsonl

    out: dict[str, dict] = {}
    for r in jsonl("extracted/legal/paragraphs.jsonl"):
        e = out.setdefault(r["law_key"], {"key": r["law_key"], "abbr": r["law"], "title": r["law_title"], "paragraphs": 0})
        e["paragraphs"] += 1
    return sorted(out.values(), key=lambda x: x["abbr"])


@router.get("/laws/{law_key}/paragraphs", response_model=list[LawParagraphEntry],
            summary="Table of contents of one law: all paragraphs in natural order, then annexes")
def law_paragraphs(law_key: str, ctx: Context = Depends(require())):
    out = service.law_paragraphs(law_key)
    if out is None:
        raise HTTPException(404, "Gesetz nicht gefunden")
    return out
