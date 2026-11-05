# PROGRESS — SV KI-Lotse

Single source of truth for all sessions. Update your row at start and at Definition of Done.

**Now:** Wave 1 merged (B, D, F, C) · WS-A agent + WS-W web running · **Next gate:** G1/G2 · **Feature freeze:** H19

## Gates (go / no-go)
- [x] **G0 (H2)** skeleton, contracts, stub API (33 paths), auth/scopes/audit, extraction, `make test` green
- [x] **G0b** Azure LLM reachable (`make smoke-llm`) — live extraction of Entlassungsbrief: 12/12 quotes verified, 5.6 s
- [ ] **G1 (H8)** hero flow clickable in cockpit; ✅ WS-B/D/F real services merged (114 tests) — API end-to-end verified: letter → eligibility → PAL080 official PDF (30 fields, ENTWURF stamp)
- [ ] **G2 (H13)** hero flow on real API incl. agent (chat + wizard share form session)
- [ ] **G3 (H19) FREEZE** evals green, Floorplan health check clean, demo script run 3×, backup video recorded
- [ ] **G4 (H23)** pitch deck (DE) done, rehearsed 3×

## Workstreams
| WS | Scope | Owner (session) | Branch | Status | Last update | Blockers |
|---|---|---|---|---|---|---|
| P0 | extraction, skeleton, contracts, docs | integrator | main | merged | H2 | — |
| WS-B | benefits catalog + eligibility, directory, legal FTS5, medications | bg agent | ws/B-benefits | merged | H5 | offices outside Wien not curated |
| WS-D | documents extraction (+golden), prevention (Impfpass) | bg agent | ws/D-documents | merged | H4 | live LLM path untested (key 401) |
| WS-F | forms: schemas, sessions, prefill, real PDF fill | bg agent | ws/F-forms | merged | H6 | Einrichtungswunsch/Senioren-WG/Reha-n-Unfall not mapped |
| WS-W | web cockpit | human session | ws/W-web | doing (re-testing on merged B/D/F) | H9 | chat needs WS-A |
| WS-A | agent orchestrator + guardrails + evals | bg agent | ws/A-agent | doing | H5 | builds against contracts; B/F stubs until merged |
| WS-C | cases + notifications | integrator | main | merged | H3 | — |

## Task checklists
- WS-W: login, header/subject switch + scopes, cockpit + inbox, Dokumente, Leistungen, Antrag-Wizard (2 s poll, PDF), Chat panel, Mein Fall, Vorsorge, Transparenz, Vertretung, 403 handling, Stellen/Medikamente/Recht — build + lint green, screenshots in `documentation/screenshots/`.

See `documentation/briefs/WS-*.md` (each brief has a checklist; copy finished items here as one line).

## Contract requests (agents → integrator)
- WS-W → WS-B: `POST /api/benefits/eligibility` returns 404 for the whole request if one `document_ids` entry has no analysis (e.g. uploaded but not analysed). Suggest skipping or reporting such documents instead. Cockpit works around it by sending only analysed documents.
- (integrator, done) `StepUpdate` gained optional `form_session_id`; `status` now optional. Shared test fixtures moved to `services/api/app/conftest.py` (`from app.conftest import auth`).

- (integrator, done) WS-D: `SourceRef.retrieved` added; `DocumentAnalysis.dropped_unverified` added + wired. Declined: enum for `extraction_mode`.
- Shared store collections: `document_analyses` (key doc id), `vaccinations` (key subject id). Demo doc ids without upload: `doc-anna-entlassung`, `doc-stefan-impfpass`, `doc-stefan-roentgen-1/-2`, `doc-stefan-bildgebung`. `make seed` loads demo PDFs + imports Stefan's Impfpass.

- WS-B: facts the eligibility engine reads (walking_unable_confirmed, treatment_type, net_income_monthly, household …) are listed in `services/api/app/services/benefits/README.md` — the agent must pass medical facts explicitly, the engine never parses quotes. New: `GET /api/benefits/rezeptgebuehr/check`, `GET /api/medications/{pharma_nr}`.

- WS-F (open): make PAL080 yes/no sections §3–§9 required (smoke test may then expect more questions); move FormPreview/PreviewItem into contracts; `FormSession.document_id`; hospital stay dates as verbatim quotes in DocumentAnalysis (→ prefill §5 von/bis). Start-session takes `?document_id=` (needs read_documents). Field ids = AcroForm names (opaque; show label_de).
- (integrator, done) `llm.chat(..., reasoning_effort=)` / `llm.json(..., reasoning_effort=)` passthrough for WS-A.

## Decisions log
- D1 Modular monolith (FastAPI routers per service) instead of microservices — same boundaries, 1/10 ops cost.
- D2 Raw data in `docs/` gitignored; deterministic extraction into committed `knowledge/extracted/` (`make extract`).
- D3 All 7 official form PDFs are AcroForms → fill official PDFs directly (no self-made layout).
- D4 Amounts only from veraendW value tables (law text can be outdated, e.g. § 5 BPGG).
- D5 Mock ID Austria: stateless token `demo-<persona>` + `X-Subject-Id`; scopes from delegations; AI inherits user's scopes.
- D7 Statute-only amounts (Satzung ÖGK § 46 Fahrtkosten, RRZ § 13 2 %-cap) are cited from the paragraph; veraendW stays primary where a table exists.
- D6 LLM: Azure AI Foundry OpenAI-v1 endpoint, model `gpt-5-4-mini`, fake mode for tests/offline.

## Cut list (→ roadmap slide)
- Real ID Austria / e-Vollmacht, ELGA & e-Impfpass API, real appointment booking, push/SMS, Honorarordnung (Steiermark 2025, wrong region), dental tariffs, other Träger (SVS, BVAEB), microservice split.
