# audit – Transparenz-Protokoll

**Purpose.** Every API call is logged by `AuditMiddleware` (`app/core/audit.py`): who (actor), for whom (subject),
via (ui / agent / service:<name>), agent tool, required scope, allowed or denied, HTTP status, cited sources and rule ids.

## Endpoints
| Method | Path | Notes |
|---|---|---|
| GET | `/api/audit?limit=` | events for the current subject, newest first (`get_context`: authenticated; the log itself is not logged) |

## Rules
Services cite sources via `ctx.cite(...)` and rules via `ctx.rule_ids`; denied calls are recorded with `allowed=false`.

## Limitations
SQLite, no retention policy or tamper protection (roadmap: append-only store, retention, export).

## Tests
`app/tests/test_smoke.py` (`test_scope_denied_is_audited`), agent tests (`via=agent`), situation integration (`via=service:situation`).
