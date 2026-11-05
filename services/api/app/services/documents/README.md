# documents

**Purpose.** Upload PDFs for the current subject. Extract only the recommendations and to-dos that a document states explicitly, each with a verbatim quote and its page. No diagnosis, no interpretation of findings, no risk statements, no therapy or medication advice (CLAUDE.md invariant 6).

## Endpoints (`/api/documents`, scope `read_documents`)
| Method | Path | |
|---|---|---|
| POST | `` | Upload a PDF (multipart `file`). Stores the bytes at `var/uploads/<doc_id>.pdf`, detects `doc_type`. Returns 415 for non-PDFs and 413 for files over 20 MB |
| GET | `` | Documents of the current subject |
| POST | `/{id}/analyze` | Runs the extraction. Stores the result in collection `document_analyses` (key = document id; WS-B and WS-F read it there) |
| GET | `/{id}/analysis` | Last stored analysis. 404 if the document has not been analysed (demo ids fall back to their golden) |
| GET | `/{id}/file` | Streams the stored PDF |

A document belonging to a different subject returns 404, so its existence is not revealed.

## Pipeline
1. `pdf.py`: pypdf text per page (the list index gives the page number), sha256, and **deterministic keyword doc-type detection** (vaccination_record → discharge_letter → imaging_report → other).
2. `extract.py`:
   - `imaging_report` and `vaccination_record` **never** produce recommendations. The boundary is enforced after extraction, so it holds even if the model returns some. Imaging reports get a notice: "Ich interpretiere keine Befunde …".
   - Otherwise, when `get_llm().live`: the prompt `prompts/extract_de.md` is sent with page-tagged text, and the JSON reply is parsed tolerantly. Unknown categories become `other`; unknown benefit ids are removed.
   - Fallback (LLM not live, or the call fails): `evals/goldens/<sha256>.json`. With no golden, the result is an empty analysis with `extraction_mode="fake"`.
3. `verify.py`: **deterministic quote verification**. A recommendation is dropped unless its `quote` occurs, whitespace-normalised, on the stated page. Hyphenated line breaks are tolerated, and quotes shorter than 15 characters are rejected. This is applied to the live and golden paths alike.

Demo ids (`doc-anna-entlassung`, `doc-stefan-impfpass`, `doc-stefan-roentgen-1`, `doc-stefan-roentgen-2`, `doc-stefan-bildgebung`) work without an upload. They are served from their golden, and only for the golden's `demo_subject_id`.

## Goldens (`evals/goldens/`)
Each golden is keyed by the sha256 of the PDF and holds only quotes and structured fields, never full document text. All quotes were hand-checked against the pypdf page text, and `tests/test_raw_pdfs.py` re-checks them whenever the PDFs are available.
- Entlassungsbefund: 12 recommendations and 8 open tasks (§9). Ids r1–r5 are identical to `app/fixtures.py`.
- Impfpass: 0 recommendations, `vaccinations` (5× COVID-19, 4× Influenza).
- Röntgen Befund, Röntgen Befund2, Befund bildgebende Diagnostik: `imaging_report`, 0 recommendations.

## Demo seeding (optional, local only)
`cd services/api && RAW_DATA_DIR=/path/to/docs uv run python -m app.services.documents.seed_demo` copies the demo PDFs into `var/uploads` under their demo ids, stores their analyses and imports Stefan's e-Impfpass.

## Sources
The document itself: every recommendation carries a quote and a page. The audit log records `"<filename>, S. <page>"` and rule `documents.quote_verification.v1`.

## Limitations
- The live path is untested against the real model because the Azure key returns 401. It is covered with a stubbed LLM.
- Scanned PDFs without a text layer produce no text and therefore no recommendations (no OCR).
- `open_tasks` are not verified (they are free text in the contract). Golden tasks were checked by hand.
- Live output wording (`text_de`) is not checked automatically. Only quote and page are verified.

## Tests
`app/services/documents/tests/`: `test_documents.py` needs no docs/ and no key. It covers upload, type detection, the proof that a fabricated quote is dropped, golden, live (stubbed) and imaging paths, and demo ids. `test_raw_pdfs.py` is skipped unless `RAW_DATA_DIR/Befunde` exists.
