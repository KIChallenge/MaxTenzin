# apps/web — KI-Lotse cockpit (WS-W)

## Purpose
German, accessible cockpit for the KI-Lotse demo: mock ID-Austria login, acting for a represented person,
documents → recommendations → benefits → form wizard → PDF draft → Mein Fall → Transparenz, plus a chat side panel.

## Run
`make web` (port 3000) or `PORT=3001 npm run dev` if 3000 is taken. API expected at `API_URL` (default http://localhost:8000).
`npm run build` and `npm run lint` must stay green.

## Architecture
- **Server components** fetch via `lib/api.ts`, which adds `Authorization: Bearer <token>`, `X-Subject-Id` and `X-Via: ui` from httpOnly cookies (`lotse_token`, `lotse_subject`, `lotse_plain`).
- **Client components** call the same-origin proxy `app/bff/[...path]/route.ts` (`/bff/api/...`), which attaches the same headers and streams binary bodies (multipart upload, PDF render). No CORS, no token in JS.
- `middleware.ts` redirects to `/login` without a token. Server actions in `app/actions.ts`: login/logout, switch subject, plain-language toggle, start form session (+ link it to the matching case step), create case from latest document.
- API types only from `lib/api-types.ts` (generated, `make openapi`), re-exported in `lib/types.ts`.
- Errors never throw: `ApiResult<T>`; `components/ApiError.tsx` renders 403 as „Dafür hat … keine Berechtigung erteilt“ + link to `/vertretung`.

## Screens
| Route | API |
|---|---|
| `/login` | `GET /api/identity/personas`, `POST /api/identity/login` |
| header (all pages) | `GET /api/identity/me`, `/represented`; scope badges |
| `/` cockpit | tiles + `GET /api/notifications` + chat entry |
| `/dokumente`, `/dokumente/[id]` | `POST /api/documents`, `POST …/analyze`, `GET …/analysis` (quote + page per recommendation) |
| `/leistungen` | `POST /api/benefits/eligibility` (status, criteria + sources, amounts with value source, next steps), „Antrag vorbereiten“ |
| `/forms/[sessionId]` | schema-driven wizard from `FormDefinition`; prefilled values with source chip; confirm/edit; missing required highlighted; polls session every 2 s (chat edits flash „gerade aktualisiert“, fields being edited are not overwritten); review; „Entwurf als PDF“ (`POST …/render`) |
| `/fall` | `GET/POST /api/cases`, `PATCH …/steps/{id}` |
| `/vorsorge` | `GET /api/prevention/overview` (wording per CLAUDE.md §8) |
| `/transparenz` | `GET /api/audit` — who · for whom · UI/KI · tool · scope · result · sources; denied rows red; repeated polling collapsed (×N) |
| `/einstellungen` | Darstellung (Einfache Sprache, Größere Schrift) + Vollmachten (scope toggles via `PUT /api/identity/delegations/{id}/scopes`, only the grantor can edit; note that real delegation runs via ID Austria). `/vertretung` redirects here |
| `/stellen`, `/medikamente`, `/recht` | directory, EKO search, legal search/paragraph (Fassung + „keine Rechtsberatung“) |
| chat panel („Lotsi“) | `POST /api/agent/chat` with page context (`form_session_id` on `/forms/<id>`, `document_ids` on `/dokumente/<id>`) so the agent works on the open form; tool trace collapsible, boundary replies highlighted, action buttons (open form, download draft, open case), minimal safe Markdown; refreshes server data after tool calls |
| `/` Lebenslage panel | `GET /api/situation` (current/planned/past episodes, effects: deadlines + hints visible, steps/prefill/facts folded), consent cards for suggestions (`…/suggestions/{id}/confirm|reject`), add dialog (`POST …/episodes`), end/remove (`PATCH`/`DELETE`); suggestions from discharge letters after upload and on the document page |
| `/` Behandlungsteam + `/einstellungen` | `GET/PUT /api/identity/care-team` – GP first, "Termin buchen" → `/termine?provider=` |
| `/termine` | `POST /api/appointments/slots/search` (topic, place, daypart, accessible; defaults from preferences), book (`POST /api/appointments`, 409 → choose again), `.ics`, cancel |
| `/einstellungen` preferences | `GET/PUT /api/identity/preferences` (PUT replaces the whole object – the form always sends the full state); voice input in the chat (SpeechRecognition de-AT) |
| documents: photos | `POST /api/documents` with `file` (PDF/photo) or `files` (several photos = one document), camera capture; `GET …/transcript` → "Was Lotsi gelesen hat" |
| `/` bundle card | `POST /api/benefits/bundles/match` – only rendered when a bundle comes back |
| sources | law → `/recht?law&nr&abs` (Absatz highlighted); document quote → `/dokumente/{id}/quelle?seite&zitat` (PDF inline via BFF `?view=1`); form → blank template PDF; Serviceratgeber → brochure PDF at the page |
| autocomplete | Medikamente + Rechtsgrundlagen: debounced (250 ms, ≥ 3 chars) typeahead over the search APIs (each lookup is audited) |

## Design
Palette after sozialversicherung.at (green / slate / light grey-blue), green darkened to `#007a4f` for WCAG AA (the original `#008e5c` is 4.18:1). No official logos or word marks. Atkinson Hyperlegible (legibility for older users). Persona „Lotsi“: a friendly little lighthouse (`components/Lotsi.tsx`) – orientation, deliberately not a person and not a doctor (medical boundary).

## Rules & knowledge
Shows only what the API returns — no amounts, eligibility or medical statements computed in the frontend. Every fact rendered with its `SourceRef` chip (quote + in-force date on hover/focus). Forms end as a draft PDF; the UI says it is never sent automatically.

## Sources
None of its own; all from the services' `SourceRef`s.

## Limitations
- No automated UI tests in repo; hero flow verified with a Playwright script (screenshots in `documentation/screenshots/`).

## Tests
`npm run build`, `npm run lint`.
