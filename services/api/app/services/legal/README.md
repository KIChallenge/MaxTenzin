# legal

## Purpose
Rechtsgrundlagen from the SozDok corpus with Fassung / in-force date. Unverbindliche Information, keine Rechtsberatung.

## Endpoints
- `GET /api/legal/paragraphs/{law_key}/{nr}` → `LegalParagraph` (law_key case-insensitive; PARA wins over ANL/ANH).
- `GET /api/legal/search?q=&law=&limit=` → `list[LegalHit]` (score: higher = better).
- `GET /api/legal/laws` → laws with paragraph count; `GET /api/legal/laws/{law_key}/paragraphs` → `list[LawParagraphEntry]`
  (table of contents: § in natural order 1, 2, 2a, 3 … then Anlagen/Anhänge; heading = last part of the heading chain,
  may be empty when the corpus has none; each entry has `nr`, `type`, `label` e.g. "§ 4" / "Anl. 1", `heading`, `in_force`;
  404 for unknown laws). Used by the cockpit's § picker on the Recht page.

## Rules & knowledge
- `service.py`: lookup + `source_ref(law_key, nr, abs)` → `SourceRef` (label "§ 46 Abs. 5 Satzung OEGK 2025",
  `in_force`), shared with benefits.
- `fts.py`: SQLite FTS5 index `var/legal_fts.db` built on first use (rebuilt when paragraphs.jsonl changes),
  `unicode61 remove_diacritics 2`, terms quoted + prefix (`"pflege"*`) OR-combined (no operator injection),
  BM25 with heading weight 3, then multiplied by a core-law boost (BPGG 1.6, RRZ/Satzung 1.4, …).

## Sources
`knowledge/extracted/legal/paragraphs.jsonl` (1,976 paragraphs, 19 laws).

## Limitations
No synonym expansion; OR semantics favour recall. Abs.-level citations are labels only (no Abs. text split).

## Tests
`app/services/legal/tests/test_legal.py`, `test_laws.py` (table of contents)
