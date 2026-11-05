# CLAUDE.md — SV KI-Lotse

Rules for every Claude Code session in this repo. Workstream details live in `documentation/briefs/WS-*.md`.

## Project in 5 lines
- 24h challenge (DVSV, Use Case 1): a personal AI navigator ("KI-Lotse") for Austrian social insurance.
- Thesis: **"KI funktioniert nur gut und vor allem sicher, wenn Prozesse definiert sind. Wir bauen sie als Top Layer auf unsere anderen Services."**
- Deterministic, source-cited services decide; the LLM only understands, routes, extracts and explains. The agent uses the same APIs and the user's delegated scopes — no special rights.
- Demo scenarios: (1) Maria acts for her mother Anna after hospital discharge (Pflegegeld, Reha, mobile Pflege, Fahrten, Rezeptgebühr); (2) Stefan's proactive prevention (e-Impfpass, Vorsorge) + child Lena; (3) boundary: imaging report → no interpretation.
- Runs locally only: `make dev` → API http://localhost:8000/docs, cockpit http://localhost:3000.

## Commands (run from repo root)
`make setup | dev | api | web | test | test-api | test-extract | eval | lint | extract | openapi | reset | smoke-llm`
Run `make test-api` (and `make lint`) before every commit that touches `services/`. Run `make openapi` after any API change.

## Language
- English: code, identifiers, comments, commits, docs in `documentation/` (except pitch + demo script).
- German: every user-facing string (UI, API `*_de` fields, agent replies). Default tone: clear, friendly, plain language on request.

## Architecture invariants (never violate)
1. Eligibility, prevention, amounts and costs are computed ONLY by deterministic services reading `knowledge/`. The LLM never decides or invents them.
2. Every fact shown to a user carries a `SourceRef` (law § + in-force date, value table + year, brochure page, form, or document quote + page). No source → don't show it.
3. Amounts come from the `values` service (veraendW) whenever a value table exists — never from law text that a table supersedes (e.g. § 5 BPGG still shows 2020 amounts) and never from model memory. Amounts/parameters that exist only in a current statute or guideline (e.g. Fahrtkosten in Satzung ÖGK 2025 § 46, 2 % cap in RRZ § 13) are cited from that paragraph via the `legal` service.
4. The agent calls services only via HTTP with the user's token + `X-Via: agent` + `X-Agent-Tool: <name>`. No direct DB/knowledge access from the agent.
5. Every endpoint uses `require(Scope...)` from `app/core/auth.py`; audit middleware logs everything automatically. Cite sources via `ctx.cite(...)`, rules via `ctx.rule_ids`.
6. Medical boundary: no diagnosis, no interpretation of findings, no risk assessment, no therapy/medication advice or dosing. From documents extract ONLY explicitly documented recommendations, each with verbatim quote + page.
7. Never submit anything. Forms end as a filled draft PDF the person reviews, signs and sends. Never fill doctor-only sections (e.g. Kur/Reha p.2 "Ärztliche Stellungnahme").
8. Prevention wording: "laut Impfplan empfohlen" / "nicht im e-Impfpass dokumentiert – bitte mit Ärztin/Arzt klären". Never "Ihnen fehlt …".
9. Legal information is "unverbindliche Information, keine Rechtsberatung"; always show the Fassung / in-force date.

## Ownership
| Path | Owner |
|---|---|
| `services/api/app/contracts/`, `app/core/`, `app/main.py`, `app/seed/`, `app/fixtures.py`, `CLAUDE.md`, `Makefile`, `knowledge/extracted/`, `tools/extract/` | integrator (main session) |
| `services/api/app/services/{benefits,directory,legal,medications,values}/`, `knowledge/benefits.yaml`, `knowledge/offices.yaml` | WS-B |
| `services/api/app/services/{documents,prevention}/`, `knowledge/prevention.yaml`, `evals/goldens/` | WS-D |
| `services/api/app/services/forms/`, `knowledge/forms/*.yaml` | WS-F |
| `services/api/app/agent/`, `evals/` (except goldens) | WS-A |
| `services/api/app/services/{cases,notifications}/` | WS-C |
| `services/api/app/services/appointments/`, `knowledge/providers.yaml` | WS-T (appointments) |
| `knowledge/benefits.yaml` + bundles/offers in `app/services/benefits/`, `knowledge/bundles.yaml`, `knowledge/prevention.yaml` (family-history rules) | WS-K2 (catalog & bundles) |
| `services/api/app/services/documents/` (image/photo upload, vision) | WS-V (vision) |
| `apps/web/` | WS-W |
Do not edit outside your paths. Need a contract/core change? Add it under **Contract requests** in `PROGRESS.md`, work around it locally, and tell the integrator.

## Conventions
- FastAPI router per service, prefix `/api/<service>`, OpenAPI tag = service name, `response_model` = contract type, `summary=` on every route.
- Pydantic v2; persistence via `app.core.db.store` (JSON doc store, collection per service); knowledge via `app.core.knowledge`.
- Tests next to code in `app/services/<name>/tests/`, run with `LLM_MODE=fake`; they must pass without `docs/` and without an API key.
- Raw data (`docs/`, gitignored) is read only by `tools/extract/` and by explicit demo/golden scripts via `RAW_DATA_DIR`.
- Frontend: Next.js App Router, server components by default, API types only from `apps/web/lib/api-types.ts` (generated).
- LLM: only via `app/core/llm.py` (Azure AI Foundry, OpenAI v1, model `gpt-5-4-mini`). `LLM_MODE=fake|live|auto`.

## Git
- Workstreams work on branch `ws/<id>-<slug>` (own worktree). Integrator merges to `main`. Never force-push `main`.
- Commit messages: `[WS-X] type: summary` (feat/fix/test/docs/refactor/chore). Small commits.
- Never commit `.env`, `docs/`, Befunde, generated PDFs or DB files.

## Definition of Done (every task)
Tests green (`make test-api`), lint clean, per-service `README.md` updated (Purpose · Endpoints · Rules & knowledge · Sources · Limitations · Tests), row in `PROGRESS.md` updated, no secrets.

## Pointers
`README.md` · `PROGRESS.md` · `documentation/architecture.md` · `documentation/briefs/` · OpenAPI http://localhost:8000/docs
