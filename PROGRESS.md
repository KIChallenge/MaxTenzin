# PROGRESS — SV KI-Lotse

Single source of truth for all sessions. Update your row at start and at Definition of Done.

**Now:** Wave 1 merged (B, D, F, C) · WS-A agent + WS-W web running · **Next gate:** G1/G2 · **Feature freeze:** H19

## Gates (go / no-go)
- [x] **G0 (H2)** skeleton, contracts, stub API (33 paths), auth/scopes/audit, extraction, `make test` green
- [x] **G0b** Azure LLM reachable (`make smoke-llm`) — live extraction of Entlassungsbrief: 12/12 quotes verified, 5.6 s
- [ ] **G1 (H8)** hero flow clickable in cockpit; ✅ WS-B/D/F real services merged (114 tests) — API end-to-end verified: letter → eligibility → PAL080 official PDF (30 fields, ENTWURF stamp)
- [ ] **G2 (H13)** hero flow on real API incl. agent — ✅ API side done (agent + evals 28/28 live); ⬜ cockpit wiring (WS-W)
- [ ] **G3 (H19) FREEZE** evals green, Floorplan health check clean, demo script run 3×, backup video recorded
- [ ] **G4 (H23)** pitch deck (DE) done, rehearsed 3×

## Workstreams
| WS | Scope | Owner (session) | Branch | Status | Last update | Blockers |
|---|---|---|---|---|---|---|
| P0 | extraction, skeleton, contracts, docs | integrator | main | merged | H2 | — |
| WS-B | benefits catalog + eligibility, directory, legal FTS5, medications | bg agent | ws/B-benefits | merged | H5 | offices outside Wien not curated |
| WS-D | documents extraction (+golden), prevention (Impfpass) | bg agent | ws/D-documents | merged | H4 | live LLM path untested (key 401) |
| WS-F | forms: schemas, sessions, prefill, real PDF fill | bg agent | ws/F-forms | merged | H6 | Einrichtungswunsch/Senioren-WG/Reha-n-Unfall not mapped |
| WS-W | web cockpit | human session | ws/W-web | review → merge requested | H10 | — (UI remarks from user follow as a 2nd small merge) |
| WS-A | agent orchestrator + guardrails + evals | bg agent | ws/A-agent | merged | H7 | evals 28/28 live (REPORT.md) |
| WS-C | cases + notifications | integrator | main | merged | H3 | — |

## Task checklists
- WS-W: login, header/subject switch + scopes, cockpit + inbox, Dokumente, Leistungen, Antrag-Wizard (2 s poll, PDF), Chat panel, Mein Fall, Vorsorge, Transparenz, Vertretung, 403 handling, Stellen/Medikamente/Recht — build + lint green, screenshots in `documentation/screenshots/`.

See `documentation/briefs/WS-*.md` (each brief has a checklist; copy finished items here as one line).

## Contract requests (agents → integrator)
- WS-W → integrator/WS-A (blocks the "chat fills the wizard" demo moment): (1) add `ChatRequest.form_session_id: str | None` — the cockpit already sends it from `/forms/<id>` (ignored today). The agent must use that session instead of `start_form` (today it creates a second session, so the open wizard never updates). (2) `set_form_fields` on choice fields: agent sent free text to `Pflegeberatung` (options Nein/Ja) → 422, then told the user „das Feld braucht einen kurzen Text, kein Ja/Nein" — wrong and confidently stated. Agent must read `options` from the definition and pass one of them; on 422 relay the validation message instead of guessing.
- WS-W → WS-A: `ChatAction(kind="open_case")` uses `url="/case"`; the cockpit route is `/fall`. Cockpit routes by `kind`, so it works — but please change to `/fall` for consistency.
- WS-W → integrator (demo risk, high): delegation scope changes live only in memory (`app/seed/loader.py` `_DELEGATIONS`). Every API restart — incl. `uvicorn --reload` whenever a file in the main checkout changes — silently restores the YAML defaults, so Anna's revoke disappears mid-demo. Persist delegation overrides in `store` (keep `reset_delegations()` for a deliberate reset), and run the demo API without `--reload`.
- WS-W → WS-F (demo risk): PAL 080 §5 is prefilled „Krankenanstalt: ja“ from the document, but von/bis/in stay empty → half-answered official form. Either prefill the stay (open item „hospital stay dates as verbatim quotes“) or don't prefill „ja“ alone. Minor: „Unterlagen: Kopie: Entlassungsbefund.pdf“ shows the technical file name; „Kopie des Entlassungsbefunds“ reads better.
- WS-W → integrator/WS-F: expose the field condition in the contract (`FormField.when`, same shape as the spec's `Condition`), so the wizard can show/hide conditional fields itself (e.g. "Andere Staatsbürgerschaft" only for "andere", proxy-only fields). Interim in the cockpit: an empty required field not listed by `next-questions` is treated as currently irrelevant and hidden; optional conditional fields cannot be hidden yet.
- WS-W → WS-F (source honesty, invariant 2): prefill labels every profile value „ID Austria Stammdaten“, incl. Personenstand, Staatsbürgerschaft, Telefon, E-Mail and SVNR. ID Austria provides name, birth date and (with consent) the ZMR main residence; the rest is not an ID-Austria attribute. Suggest „ID Austria“ only for name/birth date/address and e.g. „Profilangaben (Demo)“ for the rest.
- WS-W → WS-D / integrator (demo risk): live extraction of `Entlassungsbefund.pdf` is not stable — 22 recommendations in one run, 10 in the next, person address/insurer sometimes missing. Recommend demo runs on golden mode (or cache the first analysis per file hash).
- WS-W → WS-B: `POST /api/benefits/eligibility` returns 404 for the whole request if one `document_ids` entry has no analysis (e.g. uploaded but not analysed). Suggest skipping or reporting such documents instead. Cockpit works around it by sending only analysed documents.
- (integrator, done) `StepUpdate` gained optional `form_session_id`; `status` now optional. Shared test fixtures moved to `services/api/app/conftest.py` (`from app.conftest import auth`).

- (integrator, done) WS-D: `SourceRef.retrieved` added; `DocumentAnalysis.dropped_unverified` added + wired. Declined: enum for `extraction_mode`.
- Shared store collections: `document_analyses` (key doc id), `vaccinations` (key subject id). Demo doc ids without upload: `doc-anna-entlassung`, `doc-stefan-impfpass`, `doc-stefan-roentgen-1/-2`, `doc-stefan-bildgebung`. `make seed` loads demo PDFs + imports Stefan's Impfpass.

- WS-B: facts the eligibility engine reads (walking_unable_confirmed, treatment_type, net_income_monthly, household …) are listed in `services/api/app/services/benefits/README.md` — the agent must pass medical facts explicitly, the engine never parses quotes. New: `GET /api/benefits/rezeptgebuehr/check`, `GET /api/medications/{pharma_nr}`.

- WS-F (open): make PAL080 yes/no sections §3–§9 required (smoke test may then expect more questions); move FormPreview/PreviewItem into contracts; `FormSession.document_id`; hospital stay dates as verbatim quotes in DocumentAnalysis (→ prefill §5 von/bis). Start-session takes `?document_id=` (needs read_documents). Field ids = AcroForm names (opaque; show label_de).
- (integrator, done) `llm.chat(..., reasoning_effort=)` / `llm.json(..., reasoning_effort=)` passthrough for WS-A.

- (integrator, done) WS-A: `ChatResponse.actions` (download_pdf/open_form/open_case, derived deterministically), `ChatRequest.document_ids`, thread-safe `core.db.engine()`. Open: move Conversation models into contracts.
- (integrator, fixes after independent live eval run 27/28): start_form idempotent per conversation (no lost answers), explicit "PDF" command renders deterministically, soft guard max 2 questions/turn → 3/3 hero runs, suite 28/28.

- (integrator, done) Polish: `DocumentAnalysis.facts` (deterministic admin facts with quote+page, e.g. Entlassungsdatum) → PAL080 "KH bis" prefilled (open questions 4→3); `FormSession.document_id`; deterministic clinical-instruction filter in documents (labs, blood pressure, medication, side effects, fluid balance → removed + notice). Declined: making PAL080 §3–§9 required (agent offers recommended yes/no questions instead).

- (integrator, done — WS-W bug reports) `ChatRequest.form_session_id`: chat edits the session open in the wizard (no parallel start_form; scripted planner too); choice/checkbox values normalised to official options before PATCH; 422 relayed verbatim ("Nicht übernommen: …"); new hard output guard: no "eingetragen/halte fest" claim without successful set_form_fields (retry with tools); `get_next_questions(include_optional)` to find recommended fields; open_case → `/fall`; delegation scope overrides persisted in store (survive restarts); `make api-demo` (no --reload). Live: Pflegeberatung=Ja lands in the open wizard session 2/2; evals 28/28.

## Decisions log
- D1 Modular monolith (FastAPI routers per service) instead of microservices — same boundaries, 1/10 ops cost.
- D2 Raw data in `docs/` gitignored; deterministic extraction into committed `knowledge/extracted/` (`make extract`).
- D3 All 7 official form PDFs are AcroForms → fill official PDFs directly (no self-made layout).
- D4 Amounts only from veraendW value tables (law text can be outdated, e.g. § 5 BPGG).
- D5 Mock ID Austria: stateless token `demo-<persona>` + `X-Subject-Id`; scopes from delegations; AI inherits user's scopes.
- D7 Statute-only amounts (Satzung ÖGK § 46 Fahrtkosten, RRZ § 13 2 %-cap) are cited from the paragraph; veraendW stays primary where a table exists.
- D8 Clinical instructions to physicians are never relisted, even if quoted verbatim (deterministic filter after LLM).
- D6 LLM: Azure AI Foundry OpenAI-v1 endpoint, model `gpt-5-4-mini`, fake mode for tests/offline.

## Cut list (→ roadmap slide)
- Real ID Austria / e-Vollmacht, ELGA & e-Impfpass API, real appointment booking, push/SMS, Honorarordnung (Steiermark 2025, wrong region), dental tariffs, other Träger (SVS, BVAEB), microservice split.
