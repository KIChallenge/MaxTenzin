# 0002 Raw data gitignored, deterministic extraction into committed knowledge (D2)
**Context:** The challenge data (`docs/`: SozDok law texts, veraendW tables, EKO, Serviceratgeber, forms, fictional Befunde) is large, partly personal-looking and must not be committed. Services need fast, reproducible, citable data at runtime.

**Decision:** `docs/` is gitignored and read only by `tools/extract/` (`make extract`) and explicit demo/golden scripts via `RAW_DATA_DIR`. The extractors are deterministic (no LLM) and write `knowledge/extracted/` plus `MANIFEST.json` (rows, source files, sha256, script version, date), which is committed.

**Consequence:** Runtime and tests never need `docs/` (`make test` runs without it); every citation resolves against a committed, hashed extract. Re-extraction is explicit and reviewable as a diff. Fictional Befunde are never committed; only hand-verified goldens with quotes are.
