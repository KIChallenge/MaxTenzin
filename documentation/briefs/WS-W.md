# WS-W — Web cockpit (human-driven session)

**Worktree:** `../MaxTenzin-web` · **Branch:** `ws/W-web` · **Owned paths:** `apps/web/` only.
Read `CLAUDE.md` first. API runs at http://localhost:8000 (`make api` from the main checkout or your worktree); OpenAPI types in `apps/web/lib/api-types.ts` (regenerate: `make openapi`).

## Start prompt (paste into a new Claude Code session in the worktree)
> Read CLAUDE.md, PROGRESS.md and documentation/briefs/WS-W.md. You own apps/web only. Work on branch ws/W-web. Build the cockpit against the running stub API. Update PROGRESS.md when you reach the Definition of Done.

## Design direction
German UI, calm public-service look (high contrast, large type, WCAG AA, keyboard friendly), Austrian-gov-neutral (no official logos/branding). Plain-language toggle. Every fact shows its source as a small chip ("§ 4 BPGG", "Serviceratgeber S. 63", "Entlassungsbrief S. 6" with quote on hover).

## Screens (all against the existing stub API)
- [ ] **Login** = mock ID Austria persona picker (`GET /api/identity/personas`, `POST /login`); store token in a cookie.
- [ ] **Header**: "Angemeldet als Maria Berger · handelt für: [Anna Berger ▾]" (`GET /api/identity/represented`, send `X-Subject-Id`), visible scopes badge.
- [ ] **Cockpit**: service tiles (Dokumente, Leistungen, Anträge, Mein Fall, Vorsorge, Zuständige Stellen, Medikamente, Rechtsgrundlagen, Transparenz) + inbox (`/api/notifications`) + "Frag den Lotsen" chat entry.
- [ ] **Dokumente**: upload, analysis view with recommendations (quote + page), "Was steht drin – und was nicht" notice.
- [ ] **Leistungen**: eligibility cards (status colour, criteria with sources, missing info, next steps, amounts with value source, "Antrag vorbereiten" button).
- [ ] **Antrag-Wizard** (`/forms/[sessionId]`): generic, schema-driven from `FormDefinition` (section steps, prefilled values with source badge, confirm/edit, only missing questions highlighted, progress), review step, "Entwurf als PDF" download. Must reflect changes made by the chat (poll session every 2 s).
- [ ] **Chat** (side panel on every page): messages + collapsible tool-call trace ("Lotse hat abgefragt: Leistungen prüfen → 6 Ergebnisse"), boundary notice styling.
- [ ] **Mein Fall**: step list with status toggles. **Vorsorge**: items with status chips + disclaimer. **Transparenz**: audit table (who, für wen, via UI/KI, tool, Berechtigung, Quellen), denied calls highlighted.
- [ ] 403 handling: friendly "Dafür hat Anna Berger keine Berechtigung erteilt" + link to Vertretung settings (scope toggles via `PUT /api/identity/delegations/{id}/scopes`).

## Definition of Done (G1)
Hero flow clickable end-to-end on stubs: login Maria → act for Anna → upload → recommendations → Leistungen → Antrag-Wizard → PDF → Mein Fall → Transparenz. `npm run build` + lint green. Screenshots in `documentation/screenshots/`. PROGRESS.md row updated.
