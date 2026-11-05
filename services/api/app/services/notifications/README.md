# notifications – Posteingang

**Purpose.** A proactive inbox **composed from other services' APIs with the user's own token** – so scopes apply
transitively (no `view_health_prevention` → no prevention items; no `manage_situation` → no Lebenslage reminders).

## Endpoints (`/api/notifications`)
| Method | Path | Notes |
|---|---|---|
| GET | `` | items of kind `prevention` (due / not documented), `situation` (Meldepflicht with Frist, Kontrolltermin), `case` (open steps) |
| POST | `/{id}/read` | mark as read (stored per subject) |

Links use cockpit routes: `/vorsorge`, `/#lebenslage`, `/fall`. Ids are stable (hash of the reminder title).

## Limitations
Computed on request (no push/SMS/e-mail – roadmap). Calls are audited with `X-Via: service:notifications`.

## Tests
`notifications/tests/test_notifications.py`, `situation/tests/test_integration.py`.
