"""Run all deterministic extractors: docs/ (raw, gitignored) -> knowledge/extracted/ (committed)."""

import eko
import forms
import legal
import serviceratgeber
import values

from common import RAW_DIR

if __name__ == "__main__":
    if not RAW_DIR.exists():
        raise SystemExit(f"Raw data dir not found: {RAW_DIR} (set RAW_DATA_DIR)")
    for mod in (legal, values, eko, serviceratgeber, forms):
        mod.main()
