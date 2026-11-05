# identity

**Purpose.** Mock ID Austria login, Vertretung (delegation) with scopes, personal preferences and the Behandlungsteam.
The agent inherits exactly the scopes of the person it acts for – no special rights.

## Endpoints (`/api/identity`)
| Method | Path | Notes |
|---|---|---|
| GET | `/personas` | demo personas (Anna, Maria, Stefan, Lena) – public |
| POST | `/login` | mock ID Austria: `{persona_id}` → token `demo-<id>` |
| GET | `/me`, `/represented` | actor, subject (`X-Subject-Id`), effective scopes; persons the actor may act for |
| GET / PUT | `/delegations`, `/delegations/{id}/scopes` | only the represented person may extend scopes; the representative may only reduce; overrides persisted |
| GET / PUT | `/preferences` | per acting person: language, Einfache Sprache, detail level, daypart, near home, accessible, voice (PUT = full replace) |
| GET / PUT | `/care-team` | Hausärztin & Co. (scope `manage_appointments`); change = "Angabe von <Name>, <Datum>" |

## Rules & sources
Scopes: `read_documents` (Dokumente lesen), `prepare_applications` (Anträge vorbereiten), `manage_appointments`
(Termine verwalten), `view_health_prevention` (Vorsorge & Impfungen), `manage_case` (Fall verwalten),
`manage_situation` (Lebenslage). Seed: `app/seed/personas.yaml`, `delegations.yaml`, `care_team.yaml`.
Care-team source label is honest: "Profil (Demo) – im Echtbetrieb aus e-card-Konsultationen".

## Limitations
Mock identity (no real ID Austria / e-Vollmacht). Delegations are cached per process: after `make reset`, restart the API.
`/me`, `/preferences`, `/delegations` use `get_context` (authenticated + audited) – no scope is needed to see one's own data.

## Tests
`app/tests/test_smoke.py` (login, scopes, revoke), `identity/tests/test_preferences.py`, `appointments/tests/test_care_team.py`.
