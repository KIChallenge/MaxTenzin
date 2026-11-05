"""legal — Rechtsgrundlagen from the SozDok corpus. REAL minimal (exact lookup + naive search). WS-L: FTS5 ranking."""

import re

from fastapi import APIRouter, Depends, HTTPException

from app.contracts.misc import LegalHit, LegalParagraph
from app.core.auth import Context, require
from app.core.knowledge import jsonl

router = APIRouter(prefix="/api/legal", tags=["legal"])


def _para(r: dict) -> LegalParagraph:
    d = r["in_force"]
    date_de = f"{d[8:10]}.{d[5:7]}.{d[0:4]}" if len(d) == 10 else d
    sym = "§" if r["type"] == "PARA" else ("Art." if r["type"] == "ART" else r["type"])
    return LegalParagraph(doc_id=r["doc_id"], law_key=r["law_key"], law=r["law"], law_title=r["law_title"], nr=r["nr"],
                          heading=r["heading"], text=r["text"], in_force=d,
                          citation_de=f"{sym} {r['nr']} {r['law']} (in Kraft seit {date_de})")


@router.get("/paragraphs/{law_key}/{nr}", response_model=LegalParagraph, summary="Exact paragraph, e.g. BPGG / 4")
def paragraph(law_key: str, nr: str, ctx: Context = Depends(require())):
    for r in jsonl("extracted/legal/paragraphs.jsonl"):
        if r["law_key"].lower() == law_key.lower() and r["nr"] == nr:
            p = _para(r)
            ctx.cite(p.citation_de)
            return p
    raise HTTPException(404, "Paragraph nicht gefunden")


@router.get("/search", response_model=list[LegalHit], summary="Keyword search (naive; WS-L replaces with FTS5)")
def search(q: str, law: str | None = None, limit: int = 10, ctx: Context = Depends(require())):
    terms = [t.lower() for t in re.findall(r"\w+", q) if len(t) > 2]
    hits = []
    for r in jsonl("extracted/legal/paragraphs.jsonl"):
        if law and r["law_key"].lower() != law.lower():
            continue
        text = (r["heading"] + " " + r["text"]).lower()
        score = sum(text.count(t) for t in terms)
        if score:
            i = min((text.find(t) for t in terms if t in text), default=0)
            hits.append(LegalHit(paragraph=_para(r), score=float(score), snippet=r["text"][max(0, i - 80): i + 220]))
    return sorted(hits, key=lambda h: -h.score)[:limit]
