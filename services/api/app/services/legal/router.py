"""legal — Rechtsgrundlagen from the SozDok corpus: exact lookup + SQLite FTS5/BM25 search. REAL (owner: WS-B)."""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.contracts.misc import LegalHit, LegalParagraph
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
