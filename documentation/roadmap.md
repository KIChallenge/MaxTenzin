# Roadmap: prototype → production

The prototype's boundaries were chosen so that each demo stand-in can be replaced behind the same contract. Order
roughly by dependency, not by effort.

## 1. Identity and delegation
| Prototype | Production | Contract impact |
|---|---|---|
| Mock ID Austria: token `demo-<persona>`, personas from YAML | Real ID Austria (OIDC) login; actor from the eID | `get_context` swaps token validation; `Context` (actor, subject, scopes) unchanged |
| Delegations + scopes from YAML, overrides in store | e-Vollmacht / Vertretungsverzeichnis, Obsorge from ZMR/court data; scopes as consent records | `effective_scopes()` reads the real register; scope names stay |
| Care team "Profil (Demo)" | derived from e-card consultations (with consent) or own entry | `GET /api/identity/care-team` unchanged |

## 2. Health data
- **ELGA / e-Impfpass API** instead of parsing an uploaded e-Impfpass PDF (`prevention/impfpass.py` → API client
  writing the same `vaccinations` collection).
- Discharge letters from ELGA e-Befunde (CDA) instead of PDF/photo upload; the extraction + quote verification
  pipeline stays, quotes then point to CDA sections.
- Screening history (last Vorsorgeuntersuchung, Koloskopie) to compute "due" by history, not by age alone.
- Re-verify Impfplan intervals against the current official Impfplan and add risk groups only via doctor-confirmed
  data (never inferred).

## 3. Träger integrations
- **Submission stays with the person** in the near term (draft PDF). Next: hand-over to the Träger's own e-services
  (e.g. meinSV / PVA online forms) with the person's explicit click — never auto-submit by the agent.
- Status feedback from the Träger (application received, decision) into Mein Fall via webhooks/polling.
- Real appointment systems (ÖGK Gesundheitszentren, practice booking platforms) behind the existing
  `slots/search` / booking contract; synthetic slots remain for demos.
- Notifications beyond the in-app inbox (push/SMS/e-Mail, opt-in).

## 4. Coverage
- **Other Träger:** SVS, BVAEB (catalog entries, forms, offices); today ÖGK/PVA/FSW Wien.
- **Offices and providers outside Wien:** Serviceratgeber S. 96–115 lists ÖGK offices for all Bundesländer; demo
  practices exist only in Wien.
- Forms not mapped yet: FSW Einrichtungswunsch, Senioren-WG, Reha nach Unfall (hospital-filled, info only).
- Familienbeihilfe amounts (not in veraendW), Pflegekarenz threshold (AVRAG § 14c, not in the corpus), Ersatzpflege /
  24-h-Förderung / Mindestsicherung amounts (guidelines outside the provided data).
- Synonym expansion for legal search and bundle matching.

## 5. Architecture and operations
- **Microservice split along existing boundaries** (ADR 0001): each service already has its own router, contract
  module and store collection, and composed endpoints already call each other over HTTP with the user's token — the
  split is a deployment change (per-service DB, service-to-service auth with token exchange), not a rewrite.
- Postgres instead of SQLite JSON store; encryption at rest for health data; retention/deletion policies (DSGVO).
- Ops: health/readiness probes per service, structured logs, tracing across agent tool calls, metrics for LLM
  latency/cost, alerting; rate limiting; secrets in a vault.
- LLM: model/version pinning with the eval suite as release gate (`make eval`), Azure content filters + Prompt Shields,
  data residency in the EU region.
- Audit log: append-only/tamper-evident storage; export for the person (Auskunftsrecht).

- **MCP server for other AI assistants (option).** Publish the same tool set (`app/agent/tools.py`) as an MCP
  server, so external assistants (e.g. a Träger's own assistant, assistive apps for people with disabilities) can use
  the services. Authorization stays the same: the person logs in with ID Austria (OAuth) and the client gets only the
  delegated scopes; every call is audited as `via: mcp:<client>`. Prerequisites: real ID Austria/OAuth (section 1),
  per-client consent and rate limits. Because guards inside a foreign client cannot be enforced, all decisions stay in
  the deterministic services (already the case) and only tools are exposed – never raw data stores.

## 6. Quality, accessibility, trust
- Accessibility audit (WCAG 2.1 AA / EN 301 549) of the cockpit; screen-reader pass; Einfache Sprache reviewed by
  plain-language editors.
- User research with relatives acting as representatives and with Träger staff.
- Clinical/legal review of the boundary templates and of every curated catalog entry; a sign-off process for
  `knowledge/` changes (each change already shows up in `make sources`).
- Larger red-team eval set (more languages, indirect injection via documents), human review of a sample of live
  conversations.

## Cut list (from PROGRESS.md, consciously out of scope for the 24 h prototype)
Real ID Austria / e-Vollmacht · ELGA & e-Impfpass API · real appointment booking · push/SMS · Honorarordnung
(Steiermark 2025, wrong region) · dental tariffs · other Träger (SVS, BVAEB) · microservice split.
