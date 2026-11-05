"""legal — paragraph lookup + citations from the committed SozDok corpus (paragraphs.jsonl)."""

from __future__ import annotations

from functools import lru_cache

from app.contracts.common import SourceKind, SourceRef
from app.contracts.misc import LegalParagraph
from app.core.knowledge import jsonl

CORPUS = "extracted/legal/paragraphs.jsonl"
_SYMBOL = {"PARA": "§", "ART": "Art.", "ANL": "Anl.", "ANH": "Anh.", "ZIFF": "Z", "INH": "Inhalt"}


def rows() -> list[dict]:
    return jsonl(CORPUS)


@lru_cache
def _index() -> dict[tuple[str, str], dict]:
    """(law_key lower, nr) -> row. PARA wins over ANL/ANH with the same nr."""
    idx: dict[tuple[str, str], dict] = {}
    for r in rows():
        k = (r["law_key"].lower(), r["nr"])
        if k not in idx or r["type"] == "PARA":
            idx[k] = r
    return idx


def date_de(iso: str) -> str:
    return f"{iso[8:10]}.{iso[5:7]}.{iso[0:4]}" if len(iso) == 10 else iso


def find(law_key: str, nr: str) -> dict | None:
    return _index().get((law_key.lower(), nr))


def short_label(r: dict, abs_: str | None = None) -> str:
    sym = _SYMBOL.get(r["type"], r["type"])
    ab = f" Abs. {abs_}" if abs_ else ""
    return f"{sym} {r['nr']}{ab} {r['law']}"


def to_paragraph(r: dict) -> LegalParagraph:
    return LegalParagraph(doc_id=r["doc_id"], law_key=r["law_key"], law=r["law"], law_title=r["law_title"], nr=r["nr"],
                          heading=r["heading"], text=r["text"], in_force=r["in_force"],
                          citation_de=f"{short_label(r)} (in Kraft seit {date_de(r['in_force'])})")


def source_ref(law_key: str, nr: str, abs_: str | None = None) -> SourceRef:
    """SourceRef for a paragraph incl. in-force date. Raises KeyError if the paragraph is not in the corpus."""
    r = find(law_key, nr)
    if r is None:
        raise KeyError(f"paragraph {law_key} {nr} not in corpus")
    return SourceRef(kind=SourceKind.law, label=short_label(r, abs_), ref=r["doc_id"], in_force=r["in_force"])
