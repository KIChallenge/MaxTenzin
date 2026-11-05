"""Shared helpers for deterministic extraction from the raw challenge data (docs/) into knowledge/extracted/."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = Path(os.environ.get("RAW_DATA_DIR", REPO_ROOT / "docs"))
if not RAW_DIR.is_absolute():
    RAW_DIR = REPO_ROOT / RAW_DIR
OUT_DIR = REPO_ROOT / "knowledge" / "extracted"
MANIFEST = OUT_DIR / "MANIFEST.json"
SCRIPT_VERSION = "1.0.0"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_many(paths: list[Path]) -> str:
    """Stable combined hash over many source files (sorted by name)."""
    h = hashlib.sha256()
    for p in sorted(paths, key=lambda x: x.name):
        h.update(p.name.encode())
        h.update(sha256_file(p).encode())
    return h.hexdigest()


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def record(name: str, *, sources: list[Path], outputs: list[Path], rows: int, notes: str = "") -> None:
    """Upsert one entry in MANIFEST.json (provenance for every extracted artefact)."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    manifest[name] = {
        "sources": sorted(str(p.relative_to(REPO_ROOT)) for p in sources)
        if len(sources) <= 20
        else [f"{len(sources)} files under {sources[0].parent.relative_to(REPO_ROOT)}"],
        "sources_sha256": sha256_many(sources),
        "outputs": sorted(str(p.relative_to(REPO_ROOT)) for p in outputs),
        "rows": rows,
        "script_version": SCRIPT_VERSION,
        "extracted_at": datetime.now(UTC).strftime("%Y-%m-%d"),
        "notes": notes,
    }
    write_json(MANIFEST, manifest)
