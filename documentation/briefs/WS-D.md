# WS-D — Documents (explicit recommendations) + Prevention (e-Impfpass, Vorsorge)

> **Historical brief** — the task as handed to the workstream at the start. Current behaviour: the service READMEs, `documentation/architecture.md` and `documentation/services.md`.

**Branch:** `ws/D-documents` · **Owned paths:** `services/api/app/services/{documents,prevention}/`, `knowledge/prevention.yaml`, `evals/goldens/`
Read `CLAUDE.md` first (medical boundary!). Contracts: `app/contracts/documents.py`, `prevention.py` — don't change (Contract requests in PROGRESS.md).

## Raw inputs
Demo PDFs are NOT in git. Read them from the main checkout: `RAW_DATA_DIR=/Users/maximilianhofmann/projects/sv_ki_challenge/MaxTenzin/docs` → `Befunde/Entlassungsbefund.pdf`, `Befunde/Impfpass.pdf`, `Befunde/Röntgen Befund.pdf`, `Befunde/Röntgen Befund2.pdf`, `Befunde/Befund bildgebende Diagnostik.pdf`. All fictional. Never commit them.
The LLM key currently returns 401 → build with **golden fallback**: live extraction when `get_llm().live`, otherwise load `evals/goldens/<sha256-of-pdf>.json`.

## Tasks — documents
- [ ] Upload: store PDF bytes under `var/uploads/<doc_id>.pdf` (gitignored), detect `doc_type` (discharge_letter / imaging_report / vaccination_record) by deterministic keywords first.
- [ ] Text per page via pypdf (keep page numbers).
- [ ] Extraction prompt `services/documents/prompts/extract_de.md`: return JSON matching `DocumentAnalysis`; ONLY explicitly documented recommendations/to-dos with verbatim `quote` and `page`; no diagnosis, no interpretation, no risk statements; `text_de` phrased "Im Dokument wird … empfohlen". Map `category` + `related_benefit_ids` (ids from WS-B list: pflegegeld, reha_onko, fsw_mobile_pflege, pflegeberatung, krankentransport, fahrtkostenzuschuss, rezeptgebuehrenbefreiung, hauskrankenpflege).
- [ ] **Quote verification (deterministic):** drop any recommendation whose `quote` is not found (whitespace-normalised) on the stated page. This is the anti-hallucination guarantee — test it.
- [ ] `open_tasks` from the discharge letter task table (§9).
- [ ] Golden JSON for Entlassungsbefund (hand-checked; start from `app/fixtures.py` ANNA_ANALYSIS, verify every quote against the PDF text) + imaging reports (→ 0 recommendations, doc_type imaging_report).
- [ ] Endpoints keep signatures; `GET /api/documents/{id}/analysis` returns the stored analysis; `GET /api/documents/{id}/file` streams the PDF (scope read_documents).

## Tasks — prevention
- [ ] Deterministic e-Impfpass parser (pypdf text of Impfpass.pdf): entries disease/date/vaccine/dose/place. Golden: 5× COVID-19, 4× Influenza (2021–2025).
- [ ] `knowledge/prevention.yaml`: rules with source per item. From data: ÖGK Serviceratgeber S. 23–25 (VU ab 18 jährlich, Darmkrebs-Vorsorge ab 45, Mammografie 45–74 alle 2 J.), S. 32 (kostenlos: Influenza, COVID-19; Herpes zoster + Pneumokokken ab 60; FSME Zuschuss; ÖGK "grundsätzlich nicht zuständig"). From Impfplan Österreich (external, cite as `kind: external`, label "Impfplan Österreich 2025/2026", url https://www.sozialministerium.gv.at/impfplan, retrieved 2026-11-05): Influenza jährlich, Diphtherie-Tetanus-Pertussis-Polio Auffrischung alle 10 J. (ab 60 alle 5 J.), COVID-19 Auffrischung für Risikogruppen/≥60 jährlich im Herbst. Mark external rules clearly.
- [ ] Engine: person (age, sex) + vaccinations + as_of date → `PreventionItem`s with status due/upcoming/up_to_date/not_documented. Golden for Stefan as_of 2026-11-05: Influenza due (last 2025-11-03), DTP-Polio not_documented, VU due/possible. For Anna (78): Zoster/Pneumo free ≥60 shown as info.
- [ ] Wording rule: never "fehlt"; always recommend clarifying with Ärztin/Arzt; disclaimer from contract.
- [ ] `POST /api/prevention/import/{document_id}` parses an uploaded Impfpass and stores vaccinations per subject; `GET /overview` uses stored vaccinations (fallback: none → all not_documented).
- [ ] Tests + per-service README.md.

## Definition of Done
`make test-api` + `make lint` green; quote verification test proves a fabricated quote is dropped; goldens committed; PROGRESS.md row updated; commits on `ws/D-documents`.
