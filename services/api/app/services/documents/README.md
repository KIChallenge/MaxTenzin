# documents

**Purpose.** Upload PDFs or photos (JPG/PNG) of documents for the current subject. Extract only the recommendations and to-dos that a document states explicitly, each with a verbatim quote and its page. No diagnosis, no interpretation of findings, no risk statements, no therapy or medication advice (CLAUDE.md invariant 6).

## Endpoints (`/api/documents`, scope `read_documents`)
| Method | Path | |
|---|---|---|
| POST | `` | Upload a PDF or photos (multipart `file`, and/or several photos under `files`, one per page in order). PDF → `var/uploads/<doc_id>.pdf`; photos → `var/uploads/<doc_id>-p<N>.jpg|png`, transcribed immediately so `doc_type` is known. Type is sniffed from the bytes. 415 for other types (HEIC gets a hint to save as JPG/PNG), for PDF + photos mixed or several PDFs, and for unreadable images; 413 over 20 MB total or more than 10 photos |
| GET | `` | Documents of the current subject |
| POST | `/{id}/analyze` | Runs the extraction. Stores the result in collection `document_analyses` (key = document id; WS-B and WS-F read it there) |
| GET | `/{id}/analysis` | Last stored analysis. 404 if the document has not been analysed (demo ids fall back to their golden) |
| GET | `/{id}/file` | Streams the stored PDF, or photo page `?page=N` (default 1) |
| GET | `/{id}/transcript` | What was read, per page: photo transcription (`mode` vision / vision-cached / fake / error, `unreadable` count, `low_resolution`) or the PDF text layer (`mode` pdf-text). 404 for demo ids without a file |

A document belonging to a different subject returns 404, so its existence is not revealed.

## Pipeline
1. `pdf.py`: pypdf text per page (the list index gives the page number), sha256, and **deterministic keyword doc-type detection** (vaccination_record → discharge_letter → imaging_report → other).
2. `extract.py`:
   - `imaging_report` and `vaccination_record` **never** produce recommendations. The boundary is enforced after extraction, so it holds even if the model returns some. Imaging reports get a notice: "Ich interpretiere keine Befunde …".
   - Otherwise, when `get_llm().live`: the prompt `prompts/extract_de.md` is sent with page-tagged text, and the JSON reply is parsed tolerantly. Unknown categories become `other`; unknown benefit ids are removed.
   - Fallback (LLM not live, or the call fails): `evals/goldens/<sha256>.json`. With no golden, the result is an empty analysis with `extraction_mode="fake"`.
3. `verify.py`: **deterministic quote verification**. A recommendation is dropped unless its `quote` occurs, whitespace-normalised, on the stated page. Hyphenated line breaks are tolerated, and quotes shorter than 15 characters are rejected. This is applied to the live and golden paths alike.

Demo ids (`doc-anna-entlassung`, `doc-stefan-impfpass`, `doc-stefan-roentgen-1`, `doc-stefan-roentgen-2`, `doc-stefan-bildgebung`) work without an upload. They are served from their golden, and only for the golden's `demo_subject_id`.

## Photos (`vision.py`)
1. Upload: bytes sniffed (`%PDF`, JPEG, PNG; HEIC detected and rejected with a German hint). PIL opens every image (EXIF orientation fixed, >60 MP rejected).
2. Transcription: one LLM call per photo (parallel, max 4), prompt `prompts/vision_transcribe_de.md`: verbatim, keep line breaks, no interpretation, unreadable parts as `[unleserlich]`. Image downscaled to 2048 px long side, sent as JPEG data URL with `detail: high`, `reasoning_effort="low"`. Cached per (prompt version, image sha256) in `vision_cache`, so the same photo always yields the same text; the per-document transcript is stored in `document_transcripts`.
3. The page texts then go through the **unchanged** PDF pipeline: keyword doc type, extraction, quote verification against the transcribed page, `enforce_boundary` incl. the CLINICAL filter, `facts.py`, analysis cache keyed by the image hash (several photos: hash over the page hashes).
4. Labels: `extraction_mode` `vision` / `vision-cached` (`fake` offline), `notice_de` gets „Aus einem Foto gelesen – bitte prüfen Sie die übernommenen Angaben.“ and, below 1400 px long side, a low-resolution notice.
5. Offline (no key): transcript with empty pages and mode `fake`, no error; analysis is the empty `fake` analysis. If the provider fails, the transcript is stored with mode `error`; `analyze` retries and answers 502 if it fails again.

Live check (not a unit test, needs `gs` + key): `uv run python -m app.services.documents.live_check_vision <pdf> --pages 1 6 --dpi 150 [--skew 3 --quality 60]`. Rendered JPGs go to `var/vision_check/` (gitignored).

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
- Live extraction varies between runs (12–21 recommendations seen for the Entlassungsbrief); every one is quote-verified. The first live result per (prompt version, file hash) is cached in `analysis_cache`, so the same file always yields the same analysis (`extraction_mode="live-cached"`).
- Clinical instructions to physicians (labs, blood pressure, medication, side effects, fluid balance) are filtered deterministically after extraction and replaced by a neutral notice (`CLINICAL` in extract.py).
- Administrative facts (`facts`, e.g. Entlassungsdatum, department) and, for discharge letters, the documented `main_diagnosis` / `secondary_diagnoses` (verbatim, for forms that ask for them, e.g. PAL 080 "Leiden") come from `facts.py` (regex, quote + page), never from the LLM. They are copied, never explained.
- Scanned PDFs without a text layer produce no text and therefore no recommendations (no OCR for PDFs; upload such pages as photos instead).
- **Photos: quote verification is weaker.** Quotes are checked against the model's own transcription, not the paper. A misread word that the extractor then quotes passes verification (seen at 72 dpi: „entsprechend“ instead of „entsprechender“). Hence the photo notice; recommendations and facts stay unconfirmed until the person checks them.
- Photos: handwriting is not reliably readable; low resolution (< 1400 px long side), blur, glare and strong skew increase misreadings. The model marks what it cannot read as `[unleserlich]`, but it can also misread without marking.
- Photos: no golden fallback (goldens are keyed by PDF hash). HEIC is not converted (no decoder installed).
- `open_tasks` are not verified (they are free text in the contract). Golden tasks were checked by hand.
- Live output wording (`text_de`) is not checked automatically. Only quote and page are verified.

## Tests
`app/services/documents/tests/`: `test_documents.py` needs no docs/ and no key. It covers upload, type detection, the proof that a fabricated quote is dropped, golden, live (stubbed) and imaging paths, and demo ids. `test_vision.py` renders synthetic PNG/JPEG pages with fictional text (PIL) and covers type sniffing, HEIC/415, multi-photo pages, offline fake mode, a stubbed live vision run through the full trust pipeline (fabricated quote dropped, clinical filtered, facts, photo notice, cache), failure retry and the PDF transcript. No real document or photo is committed. `test_raw_pdfs.py` is skipped unless `RAW_DATA_DIR/Befunde` exists.
