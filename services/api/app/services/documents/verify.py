"""Deterministic quote verification — the anti-hallucination guarantee.

A recommendation survives only if its `quote` occurs (whitespace-normalised) on the page it claims.
"""

from __future__ import annotations

import re

from app.contracts.documents import Recommendation
from app.services.documents.pdf import normalize

MIN_QUOTE_LEN = 15


def _variants(page_text: str) -> list[str]:
    # pypdf keeps line-break hyphenation ("Kap-\npel"); accept both joined and kept hyphen forms.
    return [
        normalize(page_text),
        normalize(re.sub(r"-\s*\n\s*", "", page_text)),
        normalize(re.sub(r"-\s*\n\s*", "-", page_text)),
    ]


def quote_on_page(quote: str, page: int, pages: list[str]) -> bool:
    q = normalize(quote)
    if len(q) < MIN_QUOTE_LEN or page < 1 or page > len(pages):
        return False
    return any(q in v for v in _variants(pages[page - 1]))


def verify_recommendations(recs: list[Recommendation], pages: list[str]) -> tuple[list[Recommendation], list[str]]:
    """Returns (kept, dropped_ids). Drops every recommendation whose quote is not verbatim on its page."""
    kept: list[Recommendation] = []
    dropped: list[str] = []
    for r in recs:
        if quote_on_page(r.quote, r.page, pages):
            kept.append(r)
        else:
            dropped.append(r.id)
    return kept, dropped
