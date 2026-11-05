"""Hand-verified golden analyses (evals/goldens/<sha256-of-pdf>.json) — offline fallback when the LLM is not live.

File format:
    {"sha256": "...", "source_filename": "...", "demo_document_id": "doc-...", "demo_subject_id": "...",
     "verified_de"/"verified": "...", "analysis": {DocumentAnalysis without document_id}, "vaccinations": [...]?}
Goldens contain only quotes + structured fields, never the full document text.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.core.config import REPO_ROOT
from app.core.db import store

GOLDENS_DIR = REPO_ROOT / "evals" / "goldens"
# Demo ids deliberately NOT seeded (live demo: Anna's letter is uploaded as photos on stage). Their goldens must not
# stand in for a document that does not exist yet – written by seed_demo, emptied by `make reset`.
HIDDEN = "demo_hidden_documents"


@lru_cache
def _all() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if GOLDENS_DIR.exists():
        for p in sorted(GOLDENS_DIR.glob("*.json")):
            data = json.loads(p.read_text(encoding="utf-8"))
            if "sha256" in data and "analysis" in data:
                out[data["sha256"]] = data
    return out


def by_sha(sha: str) -> dict | None:
    return _all().get(sha)


def hidden(document_id: str) -> bool:
    """True if this demo id was skipped when seeding: no golden fallback until a real upload exists."""
    return store.get(HIDDEN, document_id) is not None


def by_demo_id(document_id: str) -> dict | None:
    if hidden(document_id):
        return None
    return next((g for g in _all().values() if g.get("demo_document_id") == document_id), None)


def all_goldens() -> list[dict]:
    return list(_all().values())


def golden_path(sha: str) -> Path:
    return GOLDENS_DIR / f"{sha}.json"
