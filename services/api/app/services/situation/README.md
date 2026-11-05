# situation — Lebenslage (WS-S)

## Purpose
The person's current care situation as overlapping **episodes** (Krankenhaus, Reha stationär/ambulant, Therapie,
zu Hause mit Unterstützung, Pflegeheim, Krankenstand, Kur), shown as one overview and changeable by the person or
their representative. Documents only produce **suggestions**; they take effect only after explicit consent
(`/confirm`). Confirmed episodes drive deterministic effects: reminders (Meldepflichten), eligibility facts, form
prefill and Mein-Fall steps.

## Endpoints (`/api/situation`, scope `manage_situation`)
| Method | Path | Notes |
|---|---|---|
| GET | `?as_of=YYYY-MM-DD` | `SituationOverview`: `current` (active), `upcoming` (planned), `past` (ended), `suggestions`, `effects`, `facts`, `summary_de` |
| POST | `/episodes` | `EpisodeCreate` → confirmed episode, source "Angabe von <Actor>, <Datum>"; `subtype` only for `therapy` (strahlentherapie, chemotherapie, physiotherapie, dialyse, sonstige); dates ISO |
| PATCH | `/episodes/{id}` | dates/institution/note; `status`: `ended` (end = today if empty), `active`/`planned` (for undated episodes). `suggested`/`rejected` → 422 (use confirm/reject) |
| DELETE | `/episodes/{id}` | remove an episode entered by mistake |
| POST | `/suggestions/from-document/{document_id}` | also needs `read_documents`; deterministic, idempotent (existing suggestions incl. rejected ones are returned, never duplicated or reset) |
| POST | `/suggestions/{id}/confirm` | consent → episode becomes effective (`confirmed_by`, `confirmed_at`); idempotent |
| POST | `/suggestions/{id}/reject` | decline; stays visible only via the document endpoint |

Episodes of another subject → 404. Create/confirm/patch add Mein-Fall steps (see below).

## Status logic
`suggested`/`rejected` are stored states and never change by date. Confirmed episodes: `ended` if ended manually or
`end < today`; `planned` if `start > today`; `active` if `start <= today`; undated episodes use the stored base
(`planned` for a suggested Reha, `ended` for a discharge-letter hospital stay without dates, otherwise `active`).
`today` is injectable (`as_of`, service functions take `today`).

## Rules & knowledge
`knowledge/situation.yaml`: type titles/phrases (summary), therapy subtypes, effect rules, sources.
- **Suggestions** (discharge letter only, `suggest_from_analysis`): hospital (end = `facts.discharge_date`, start from
  `admission_date` if present, institution = `facts.institution`/`department` with its own quote); home_care since
  discharge if a *care* recommendation documents Hauskrankenpflege/mobile Pflege/Körperpflege; therapy
  `strahlentherapie` if a quote mentions Strahlentherapie/Bestrahlung (preferring the page-text sentence
  "Die Bestrahlung erfolgt ambulant …" and taking `end_estimate_de` like "Mitte November 2026" from a quote
  "Abschluss … <Mitte|Anfang|Ende> <Monat> <Jahr>"; page text only when the PDF is stored for the subject); rehab
  planned (undated) if a *rehabilitation* recommendation exists. Each carries the verbatim quote + page. Only the
  episode type and administrative dates are taken over — no diagnosis, no therapy content.
- **Reminders** (only if Pflegegeld is involved: fact `receives_pflegegeld`/`pflegegeld_applied`, a Mein-Fall step
  with `benefit_id: pflegegeld`, or a PAL 080 form session): hospital/rehab_inpatient/cure → "… binnen 4 Wochen an
  die PVA melden", due = start (or end) + 28 days; nursing_home → Aufnahme ins Pflegeheim melden. Source: PAL 080
  Meldepflichten (PDF p. 6, "Pflegegeld – Meldefrist: 4 Wochen"). Hospital ended ≤ 8 weeks ago → "Hausärztliche
  Kontrolle vereinbaren" (`key: appointment:hausarzt_kontrolle`, `value: hausarzt_kontrolle` = appointments topic),
  sourced with the letter's follow-up quote when available.
- **Hints:** "Pflegegeld ruht während eines stationären Aufenthalts" for active/planned stationary stays with
  Pflegegeld involved, cited as **§ 12 Abs. 1 BPGG** (text checked in `paragraphs.jsonl`: ruht ab dem Tag nach der
  Aufnahme, wenn SV/Landesgesundheitsfonds/Bund/KFA überwiegend die Kosten trägt). Not shown if the paragraph is
  missing from the corpus.
- **Facts** (active episodes only): therapy strahlentherapie/chemotherapie/dialyse → `treatment_type`; hospital →
  `in_hospital`; rehab → `in_rehab`; home_care → `living_at_home_with_support`; nursing_home → `in_nursing_home`;
  sick_leave → `sick_leave`.
- **Prefill** (forms rule kind `situation.<key>`, implemented in `forms/prefill.py`, confirmed episodes only, and only
  if the actor has `manage_situation` for the subject): stationary stays (hospital, rehab_inpatient, cure,
  nursing_home; active or ended ≤ 365 days), most recent first → `stay.any`, `stay1.*`/`stay2.*`
  (`start`, `end`, `institution`); `hospital.*`; ended Reha/Kur ≤ 5 years → `rehab5y.any`, `rehab5y_N.when|where`;
  active therapy → `therapy.kind|institution`. Rules may chain alternatives (`situation.stay1.end|document.discharge_date`);
  a known-but-empty situation value stops the chain so two stays are never mixed. Used in PAL 080 § 5, Kur/Reha
  "Frühere Aufenthalte" and ÖGK Fahrtkosten "Art der Behandlung"/"Behandler/in".
- **Case steps** (deterministic ids `sit-<episode>-<rule>`, added once to the subject's most recent case):
  "Spitalsaufenthalt an die PVA melden (bis …)", "Reha antreten", "Nach der Reha: Pflegebedarf neu einschätzen lassen".
  The case list is read via `GET /api/cases` with the user's token (so `manage_case` applies); the append is a
  store write until cases offers `POST /api/cases/{id}/steps` (contract request).

## Integration (pure functions in `service.py`)
`situation_facts(subject_id, today=None) -> dict` · `situation_reminders(subject_id, today=None, facts=None) -> list[Effect]`
· `prefill_keys(subject_id, today=None)` · `overview(subject_id, today=None)`.

## Sources
Every episode has a `SourceRef` (document quote + page, or "Angabe von <Name>, <Datum>"); every effect carries one
(episode source, PAL 080 Meldepflichten, § 12 Abs. 1 BPGG with in-force date).

## Limitations
- Only discharge letters produce suggestions. Without the stored PDF (golden fallback) the therapy suggestion quotes
  the Reha recommendation ("… nach Abschluss der geplanten Strahlentherapie") and has no end estimate.
- "Pflegegeld involved" is inferred from Mein Fall / form sessions; whether a stay is at SV cost is not checked
  (stated in the reminder text). Case steps are idempotent per episode + rule; re-dating an episode later does not
  update an existing step (its title keeps the original due date).
- Suggestion ids are per document (`sug-<document_id>-<rule>`).

## Tests
`tests/test_situation.py` (suggestions with quotes, no effect before confirm, confirm → facts/reminders/prefill/case
steps, idempotency, 403 without `manage_situation` / `read_documents`, 404 for other subjects, status transitions
with injected `today`, validation) and `forms/tests/test_prefill_situation.py` (situation vs. document fallback,
no mixing, scope check, Kur/Reha previous stays). Run `make test-api`.
