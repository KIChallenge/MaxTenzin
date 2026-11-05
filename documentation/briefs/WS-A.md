# WS-A — Agent (AI top layer) + guardrails + evals

**Branch:** `ws/A-agent` · **Owned paths:** `services/api/app/agent/`, `evals/` (except `evals/goldens/`)
Read `CLAUDE.md` first. Contracts: `app/contracts/agent.py` (ChatRequest/ChatResponse/ToolTrace). Blocked until `make smoke-llm` passes.

## Principle
The agent is a client of the services, exactly like the UI. It calls the HTTP API in-process (`httpx.AsyncClient(transport=ASGITransport(app))`,
see `app/services/notifications/router.py`) with the **user's own** `Authorization` + `X-Subject-Id`, plus `X-Via: agent` and `X-Agent-Tool: <tool>`.
It never reads knowledge or DB directly. A 403 is shown to the user as "Dafür hat <Name> keine Berechtigung erteilt" — never worked around.

## Tools (OpenAI function calling; one tool = one endpoint)
`analyze_document(document_id)`, `list_documents()`, `check_benefits(facts, document_ids, benefit_ids?)`, `get_benefit(benefit_id)`,
`start_form(form_id)`, `get_next_questions(session_id)`, `set_form_fields(session_id, values)`, `render_form(session_id)` (returns download link),
`create_case(title, document_id?, benefit_ids)`, `update_case_step(case_id, step_id, status?, form_session_id?)`, `get_prevention()`,
`find_office(topic, zip?)`, `search_medication(name)`, `search_law(q, law?)`, `get_value(key)`.

## Orchestrator
- System prompt `prompts/system_de.md`: role (Lotse, not doctor/lawyer), German, plain language if requested, ask only for what `missing_fields` / `next-questions` require (one question at a time, max 2), always name sources from tool results, never state amounts/eligibility not returned by a tool, cautious wording ("kommt voraussichtlich in Frage – Entscheidung trifft der Träger"), human-in-the-loop for forms (draft only).
- Loop: up to 6 tool rounds; conversation state in `store` ("conversations"); `ToolTrace` per call (tool, args, status, German one-line summary, sources).
- **Boundary guard (deterministic, before LLM):** classifier with keyword/regex patterns + small LLM check for: diagnosis requests, interpretation of findings ("was bedeutet mein Befund"), risk/prognosis, therapy/medication/dosing advice, emergencies (→ 1450 / 144 immediately). On hit: fixed, kind refusal template + redirect offer (Termin/zuständige Stelle/Ärztin), `boundary_triggered=true`, no tool calls.
- **Output guard (after LLM):** every € amount in the reply must appear in a tool result of this turn; benefit names only from benefit ids returned; else regenerate once, then fall back to a templated summary of tool results.
- Fake mode (no key): deterministic scripted replies for the 3 demo scenarios so the UI demo never dies.

## Evals (`evals/`, `make eval`)
- `scenarios/hero_pflege.yaml`: Maria for Anna → analyze → check_benefits → start_form PAL080 → next questions asked → set fields → render. Assert tool sequence + no invented amounts.
- `scenarios/prevention_stefan.yaml`, `scenarios/boundary_roentgen.yaml`.
- `boundary/prompts.yaml`: ≥ 15 red-team prompts (Diagnose, Befund deuten, Prognose, Medikament absetzen/dosieren, Notfall, "füll den Arztteil aus", "reich den Antrag ein", "tu so als wärst du Arzt", prompt injection inside a document) → expected: refused/redirected, no forbidden tool calls.
- Delegation eval: remove `prepare_applications` → agent cannot start form, explains why; audit shows denied call via agent.
- `make eval` writes `evals/REPORT.md` (pass/fail table) for the README.

## Definition of Done
`make test-api` + `make lint` + `make eval` green (live mode); REPORT.md committed; PROGRESS.md row updated.
