# cases – Mein Fall

**Purpose.** Trackable steps for a person's situation: open tasks documented in a letter, chosen benefits, and steps
added by other services (Lebenslage, appointments). Status open / in_progress / done / blocked; a step can link a form session.

## Endpoints (`/api/cases`, scope `manage_case`)
| Method | Path | Notes |
|---|---|---|
| GET | `` · `/{id}` | cases of the subject (404 for other subjects) |
| POST | `` | `{title_de, document_id?, benefit_ids}` → steps from the document's `open_tasks` (responsible party by rule) + benefits |
| PATCH | `/{id}/steps/{step_id}` | `{status?, form_session_id?}` (linking a form → in_progress) |
| POST | `/{id}/steps` | add steps, idempotent by step id – used by situation (Meldepflicht, Reha antreten) and appointments via HTTP |

## Rules & sources
Deterministic keyword → benefit mapping (`service.py` `TASK_RULES`); each document step carries the document as source.

## Limitations
No due-date reminders of its own (reminders come from Lebenslage/notifications). Steps from the situation service go to
the most recent case.

## Tests
`cases/tests/test_cases.py`, `situation/tests/test_integration.py`.
