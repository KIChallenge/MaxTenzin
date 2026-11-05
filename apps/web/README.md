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
| `/vertretung` | delegations; toggles via `PUT /api/identity/delegations/{id}/scopes` (only grantor can edit) |
| `/stellen`, `/medikamente`, `/recht` | directory, EKO search, legal search/paragraph (Fassung + „keine Rechtsberatung“) |
| chat panel | `POST /api/agent/chat`; tool trace collapsible, boundary replies highlighted, refreshes server data after tool calls |

## Rules & knowledge
Shows only what the API returns — no amounts, eligibility or medical statements computed in the frontend. Every fact rendered with its `SourceRef` chip (quote + in-force date on hover/focus). Forms end as a draft PDF; the UI says it is never sent automatically.

## Sources
None of its own; all from the services' `SourceRef`s.

## Limitations
- Chat depends on WS-A; on the current stub it returns 500 (LLM key, G0b) → shown as „Der Lotse ist gerade nicht erreichbar“.
- On `main` the real cases service needs a stored document analysis; the documents stub doesn't store one, so „Fall aus Dokument anlegen“ returns 404 until WS-D is merged.
- No automated UI tests in repo; hero flow verified with a Playwright script (screenshots in `documentation/screenshots/`).

## Tests
`npm run build`, `npm run lint`.
