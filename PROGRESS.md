# PROGRESS — SV KI-Lotse

Single source of truth for all sessions. Update your row at start and at Definition of Done.

**Now:** Phase 0 done → Wave 1 running · **Next gate:** G1 · **Feature freeze:** H19

## Gates (go / no-go)
- [x] **G0 (H2)** skeleton, contracts, stub API (33 paths), auth/scopes/audit, extraction, `make test` green
- [x] **G0b** Azure LLM reachable (`make smoke-llm`) — live extraction of Entlassungsbrief: 12/12 quotes verified, 5.6 s
- [ ] **G1 (H8)** hero flow clickable in cockpit on stubs; WS-B/D/F real services merged
- [ ] **G2 (H13)** hero flow on real API incl. agent (chat + wizard share form session)
- [ ] **G3 (H19) FREEZE** evals green, Floorplan health check clean, demo script run 3×, backup video recorded
- [ ] **G4 (H23)** pitch deck (DE) done, rehearsed 3×

## Workstreams
| WS | Scope | Owner (session) | Branch | Status | Last update | Blockers |
|---|---|---|---|---|---|---|
| P0 | extraction, skeleton, contracts, docs | integrator | main | merged | H2 | — |
| WS-B | benefits catalog + eligibility, directory, legal FTS5, medications | bg agent | ws/B-benefits | doing | — | — |
| WS-D | documents extraction (+golden), prevention (Impfpass) | bg agent | ws/D-documents | merged | H4 | live LLM path untested (key 401) |
| WS-F | forms: schemas, sessions, prefill, real PDF fill | bg agent | ws/F-forms | doing | — | — |
| WS-W | web cockpit | human session | ws/W-web | todo | — | — |
| WS-A | agent orchestrator + guardrails + evals | bg agent | ws/A-agent | doing | H5 | builds against contracts; B/F stubs until merged |
| WS-C | cases + notifications | integrator | main | merged | H3 | — |

## Task checklists
See `documentation/briefs/WS-*.md` (each brief has a checklist; copy finished items here as one line).

## Contract requests (agents → integrator)
- (integrator, done) `StepUpdate` gained optional `form_session_id`; `status` now optional. Shared test fixtures moved to `services/api/app/conftest.py` (`from app.conftest import auth`).

- (integrator, done) WS-D: `SourceRef.retrieved` added; `DocumentAnalysis.dropped_unverified` added + wired. Declined: enum for `extraction_mode`.
- Shared store collections: `document_analyses` (key doc id), `vaccinations` (key subject id). Demo doc ids without upload: `doc-anna-entlassung`, `doc-stefan-impfpass`, `doc-stefan-roentgen-1/-2`, `doc-stefan-bildgebung`. `make seed` loads demo PDFs + imports Stefan's Impfpass.

## Decisions log
- D1 Modular monolith (FastAPI routers per service) instead of microservices — same boundaries, 1/10 ops cost.
- D2 Raw data in `docs/` gitignored; deterministic extraction into committed `knowledge/extracted/` (`make extract`).
- D3 All 7 official form PDFs are AcroForms → fill official PDFs directly (no self-made layout).
- D4 Amounts only from veraendW value tables (law text can be outdated, e.g. § 5 BPGG).
- D5 Mock ID Austria: stateless token `demo-<persona>` + `X-Subject-Id`; scopes from delegations; AI inherits user's scopes.
- D6 LLM: Azure AI Foundry OpenAI-v1 endpoint, model `gpt-5-4-mini`, fake mode for tests/offline.

## Cut list (→ roadmap slide)
- Real ID Austria / e-Vollmacht, ELGA & e-Impfpass API, real appointment booking, push/SMS, Honorarordnung (Steiermark 2025, wrong region), dental tariffs, other Träger (SVS, BVAEB), microservice split.
