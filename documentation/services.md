# Service endpoints

All endpoints of the API, grouped by service (= OpenAPI tag). **69 operations on 61 paths** (FastAPI `app.openapi()`).
The Scope column is read from the code, not hand-written: it is the `require(Scope.…)` dependency of each route
(`app/core/auth.py`), plus `Scope.…` checks found in the route handler. Interactive spec: http://localhost:8000/docs.

- **public** — no token needed (persona list, demo login, health).
- **login** — a valid demo token (`Authorization: Bearer demo-<persona>`) and, when acting for someone else, a
  delegation from that person (`X-Subject-Id`); otherwise 401 / 403. No further scope.
- **`scope`** — additionally the named scope for the subject; missing → 403, recorded in the audit log with
  `allowed=false`. The agent sends the user's own token, so the same check applies to every tool call.
- **Also checked in handler** — a second scope checked inside the route for one optional part of the request.

Scopes (German labels as shown in the cockpit, `apps/web/lib/labels.ts`):

| Scope | Label (DE) | Guards |
|---|---|---|
| `read_documents` | Dokumente lesen | documents; document-based prefill / eligibility / Lebenslage suggestions |
| `prepare_applications` | Anträge vorbereiten | form sessions (wizard + chat), PDF draft |
| `manage_appointments` | Termine verwalten | slot search, booking, Behandlungsteam |
| `view_health_prevention` | Vorsorge- und Gesundheitsdaten einsehen | e-Impfpass, Vorsorge; prevention items in bundles and inbox |
| `manage_case` | Fall verwalten | Mein Fall (also when other services add steps) |
| `manage_situation` | Lebenslage | episodes, suggestions, effects; Lebenslage facts in eligibility and prefill |

Acting for oneself grants all scopes; acting for someone else grants exactly the delegation's scopes.

Checks that live in helper functions (not visible in the tables):
- `POST /api/benefits/eligibility`, `POST /api/benefits/bundles/match`: `document_ids` need `read_documents` (else 403);
  unanalysed or foreign documents are skipped (audit rule `benefits.document_skipped:<id>`).
- Bundles: prevention items only with `view_health_prevention` (else skipped, audit `bundles.prevention_skipped_no_scope`).
- Eligibility (`benefits`) and form prefill (`forms/prefill.py`) use Lebenslage facts only if the caller has
  `manage_situation` for the subject.
- `PUT /api/identity/delegations/{id}/scopes`: only the grantor may extend scopes; the grantee may only reduce them.
- Composed endpoints (`GET /api/notifications`, situation → cases, appointments → cases) call the other services over
  HTTP with the caller's token, so those services' scopes apply transitively (see `architecture.md`).
- Every subject-owned record (document, session, case, episode, appointment, conversation) of another subject → 404.

## identity (10)

| Method | Path | Scope | Also checked in handler | Summary |
|---|---|---|---|---|
| GET | `/api/identity/personas` | public |  | Demo personas (mock ID Austria) |
| POST | `/api/identity/login` | public |  | Mock ID Austria login |
| GET | `/api/identity/me` | login |  | Current actor, subject and effective scopes |
| GET | `/api/identity/represented` | login |  | Persons the actor may act for (incl. self) |
| GET | `/api/identity/delegations` | login |  | Delegations granted by the subject |
| PUT | `/api/identity/delegations/{delegation_id}/scopes` | login |  | Grantor changes scopes (demo) |
| GET | `/api/identity/preferences` | login |  | Preferences of the acting person |
| PUT | `/api/identity/preferences` | login |  | Save preferences (language, detail, daypart …) |
| GET | `/api/identity/care-team` | `manage_appointments` |  | Behandlungsteam (Hausärztin u. a.) of the subject |
| PUT | `/api/identity/care-team` | `manage_appointments` |  | Set/change e.g. the Hausärztin (person's own choice) |

## situation (7)

| Method | Path | Scope | Also checked in handler | Summary |
|---|---|---|---|---|
| GET | `/api/situation` | `manage_situation` |  | Current Lebenslage: episodes, suggestions, effects |
| POST | `/api/situation/episodes` | `manage_situation` |  | Add an episode (set by the person/representative) |
| PATCH | `/api/situation/episodes/{episode_id}` | `manage_situation` |  | Change dates/status (e.g. end an episode) |
| DELETE | `/api/situation/episodes/{episode_id}` | `manage_situation` |  | Remove an episode entered by mistake |
| POST | `/api/situation/suggestions/from-document/{document_id}` | `manage_situation` | `read_documents` | Suggest episodes from an analysed document (NOT applied until confirmed) |
| POST | `/api/situation/suggestions/{episode_id}/confirm` | `manage_situation` |  | Consent: apply a suggestion |
| POST | `/api/situation/suggestions/{episode_id}/reject` | `manage_situation` |  | Decline a suggestion |

## documents (6)

| Method | Path | Scope | Also checked in handler | Summary |
|---|---|---|---|---|
| POST | `/api/documents` | `read_documents` |  | Upload a PDF or photos (JPG/PNG) of a document for the current subject |
| GET | `/api/documents` | `read_documents` |  | Documents of the current subject |
| POST | `/api/documents/{document_id}/analyze` | `read_documents` |  | Extract explicitly documented recommendations |
| GET | `/api/documents/{document_id}/analysis` | `read_documents` |  | Last analysis result |
| GET | `/api/documents/{document_id}/file` | `read_documents` |  | Download the uploaded PDF (or photo page ?page=N) |
| GET | `/api/documents/{document_id}/transcript` | `read_documents` |  | Text read from the document, per page (photo transcription or PDF text layer) |

## benefits (8)

| Method | Path | Scope | Also checked in handler | Summary |
|---|---|---|---|---|
| PATCH | `/api/benefits/facts` | login |  | Store answers (merge; value null deletes). Provenance: who, when, via cockpit/Lotsi |
| GET | `/api/benefits/facts` | login |  | Answers given so far for the subject (shared by cockpit and Lotsi), with provenance |
| GET | `/api/benefits` | login |  | Benefit catalog (benefits and offers) |
| GET | `/api/benefits/rezeptgebuehr/check` | login |  | Rezeptgebühr calculator: befreit / Obergrenze 2 % / nicht befreit |
| GET | `/api/benefits/{benefit_id}` | login |  | One benefit incl. legal basis and sources |
| POST | `/api/benefits/eligibility` | login |  | Deterministic eligibility check |
| GET | `/api/benefits/bundles/catalog` | login |  | All situation bundles (Pflege, nach dem Spital, …), evaluated for the current person |
| POST | `/api/benefits/bundles/match` | login |  | Bundle for a situation (id or free text) + facts; null if the text matches no situation |

## prevention (2)

| Method | Path | Scope | Also checked in handler | Summary |
|---|---|---|---|---|
| GET | `/api/prevention/overview` | `view_health_prevention` |  | Vaccination history + due prevention items |
| POST | `/api/prevention/import/{document_id}` | `view_health_prevention` |  | Import vaccinations from an uploaded e-Impfpass PDF |

## forms (10)

| Method | Path | Scope | Also checked in handler | Summary |
|---|---|---|---|---|
| GET | `/api/forms` | login |  | Available form definitions |
| GET | `/api/forms/definitions/{form_id}` | login |  | One form definition (wizard + agent) |
| POST | `/api/forms/definitions/{form_id}/sessions` | `prepare_applications` | `read_documents` | Start a prefilled form session |
| GET | `/api/forms/sessions/{session_id}` | `prepare_applications` |  | Current session values |
| GET | `/api/forms/sessions/{session_id}/next-questions` | `prepare_applications` |  | Only missing required fields (optionally also recommended ones) |
| PATCH | `/api/forms/sessions/{session_id}` | `prepare_applications` |  | Set field values (wizard or agent) |
| GET | `/api/forms/sessions/{session_id}/preview` | `prepare_applications` |  | Review step: label, value and source of every filled field |
| POST | `/api/forms/sessions/{session_id}/render` | `prepare_applications` |  | Render filled official PDF (draft – never submitted) |
| GET | `/api/forms/definitions/{form_id}/template` | login |  | Blank official form PDF (as published by the Träger) |
| GET | `/api/forms/brochures/serviceratgeber` | login |  | ÖGK Serviceratgeber 2026 PDF (only if the raw data folder is present) |

## cases (5)

| Method | Path | Scope | Also checked in handler | Summary |
|---|---|---|---|---|
| GET | `/api/cases` | `manage_case` |  | Cases of the current subject |
| GET | `/api/cases/{case_id}` | `manage_case` |  | One case |
| POST | `/api/cases` | `manage_case` |  | Create case from a document's open tasks + selected benefits |
| PATCH | `/api/cases/{case_id}/steps/{step_id}` | `manage_case` |  | Update step status and/or link a form session |
| POST | `/api/cases/{case_id}/steps` | `manage_case` |  | Add steps (idempotent by step id) – used by other services |

## appointments (6)

| Method | Path | Scope | Also checked in handler | Summary |
|---|---|---|---|---|
| GET | `/api/appointments/providers` | login |  | Providers by topic/kind/postcode |
| POST | `/api/appointments/slots/search` | `manage_appointments` |  | Free slots matching preferences (near, daypart …) |
| POST | `/api/appointments` | `manage_appointments` |  | Book a slot (demo) – links to Mein Fall |
| GET | `/api/appointments` | `manage_appointments` |  | Appointments of the current subject |
| POST | `/api/appointments/{appointment_id}/cancel` | `manage_appointments` |  | Cancel an appointment |
| GET | `/api/appointments/{appointment_id}/ics` | `manage_appointments` |  | Calendar file (.ics) |

## notifications (2)

| Method | Path | Scope | Also checked in handler | Summary |
|---|---|---|---|---|
| GET | `/api/notifications` | login |  | Proactive notifications for the current subject |
| POST | `/api/notifications/{notification_id}/read` | login |  | Mark a notification as read |

## directory (1)

| Method | Path | Scope | Also checked in handler | Summary |
|---|---|---|---|---|
| GET | `/api/directory/offices` | login |  | Responsible offices by topic and postcode |

## medications (2)

| Method | Path | Scope | Also checked in handler | Summary |
|---|---|---|---|---|
| GET | `/api/medications/search` | login |  | Search EKO by product name |
| GET | `/api/medications/{pharma_nr}` | login |  | One EKO pack by Pharmazentralnummer |

## legal (3)

| Method | Path | Scope | Also checked in handler | Summary |
|---|---|---|---|---|
| GET | `/api/legal/paragraphs/{law_key}/{nr}` | login |  | Exact paragraph, e.g. BPGG / 4 |
| GET | `/api/legal/search` | login |  | Full-text search (SQLite FTS5, BM25, core-law boost) |
| GET | `/api/legal/laws` | login |  | All laws/guidelines in the corpus: key, abbreviation, title, paragraph count |

## values (2)

| Method | Path | Scope | Also checked in handler | Summary |
|---|---|---|---|---|
| GET | `/api/values/{key}` | login |  | One value for a year (default 2026) |
| GET | `/api/values` | login |  | All mapped values for a year |

## audit (1)

| Method | Path | Scope | Also checked in handler | Summary |
|---|---|---|---|---|
| GET | `/api/audit` | login |  | Audit events for the current subject (newest first) |

## agent (3)

| Method | Path | Scope | Also checked in handler | Summary |
|---|---|---|---|---|
| POST | `/api/agent/chat` | login |  | Chat with Lotsi (KI-Lotse agent) |
| GET | `/api/agent/conversations` | login |  | Conversations of the actor for the subject |
| GET | `/api/agent/conversations/{conversation_id}` | login |  | Conversation history incl. traces |

## meta (1)

| Method | Path | Scope | Also checked in handler | Summary |
|---|---|---|---|---|
| GET | `/api/health` | public |  | health |

