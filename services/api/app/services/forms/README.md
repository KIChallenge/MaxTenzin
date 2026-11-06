# forms — one schema, two clients, real PDF fill

## Purpose
The wizard UI and the AI agent fill the **same form session** from the **same schema**. `next-questions` returns only
what is still missing, so the agent asks only what is needed. The result is the **official PDF**, filled and stamped
"ENTWURF – bitte prüfen und selbst unterschreiben". Nothing is ever submitted.

## Endpoints (`/api/forms`, scope `prepare_applications` for sessions)
| Method | Path | Notes |
|---|---|---|
| GET | `` | all form definitions (from YAML) |
| GET | `/definitions/{form_id}` | one `FormDefinition` (PDF mapping stays internal) |
| GET | `/definitions/{form_id}/template` | blank official PDF as published by the Träger (login only) |
| GET | `/brochures/serviceratgeber` | ÖGK Serviceratgeber 2026 PDF, only if the raw data folder is present (cited pages open in the cockpit) |
| POST | `/definitions/{form_id}/sessions?document_id=` | start a prefilled session (uuid id). `document_id` (optional, needs `read_documents`) adds document facts (quote + page) from `store('document_analyses')` |
| GET | `/sessions/{id}` | session values (`FieldValue` with `SourceRef`, `confirmed`) |
| GET | `/sessions/{id}/next-questions?include_optional=` | required + relevant + empty + not doctor-only, in section order; `include_optional=true` also returns recommended questions |
| PATCH | `/sessions/{id}` | set values; validated (type, options, dates `TT.MM.JJJJ`/ISO, doctor-only) → 422 `{"message_de", "fields": {id: msg}}` |
| GET | `/sessions/{id}/preview` | review step: label, value, source, missing for every relevant field |
| POST | `/sessions/{id}/render` | filled official PDF (download, `NeedAppearances`, draft stamp on every page); status → `rendered` |

Sessions are scoped to the subject (other subjects get 404). Status: `draft` → `ready` (no required question left) → `rendered`.

## Rules & knowledge
- Schemas: `knowledge/forms/<form_id>.yaml`, validated by pydantic models in `spec.py`; `knowledge/schema/form.schema.json`
  is generated from them (`uv run python -m app.services.forms.spec`) and a test keeps it in sync.
- Per field: `pdf_field` (defaults to `id`), `pdf_on_value` (checkbox), `pdf_options` (choice → radio export state),
  `pdf_overflow` + `max_chars` (long text continues on the form's next line), `when` (relevance: other field value or
  `proxy`; chained: a follow-up of a question that no longer applies does not apply either), `required` /
  `recommended`, `ask_hint_de`, `prefill`, `blank_from_prefill`, `pattern` + `pattern_hint_de` (regex for the
  normalized text, e.g. a package count – an unknown answer is a 422, never „nicht bekannt“), `doctor_only` +
  `readonly_reason_de`. `blank_from_prefill: true`: a prefill that resolves to `""` *with* a source means "known:
  leave empty" – the empty value is stored with its source and `next-questions` does not ask for it again.
- Prefill (`prefill.py`): `profile.*` (subject), `actor.*` + `delegation.*` (only when acting for someone else),
  `document.*` (admin facts from the analysis, quote + page), `situation.*` (confirmed Lebenslage episodes, only if
  the actor has `manage_situation`; see `situation/README.md`), `facts.*` (answers already given for the benefit
  checks via cockpit or Lotsi, `GET /api/benefits/facts`; source = „Angabe von <Name>, <Datum> (Lotsi|Cockpit) – bitte
  prüfen“; numbers as German amounts „1.150,00“), `system.today` / `system.city_today`, `const:` (a suggestion). Rules may
  chain alternatives (`situation.stay1.end|document.discharge_date`). Every prefill carries a `SourceRef` and starts
  `confirmed: false`. Profile sources are labelled honestly: "ID Austria" only for name/birth date, "ID Austria –
  Hauptwohnsitz laut ZMR" for the address, "e-card / Sozialversicherung" for SVNR/insurer, everything else
  "Profilangaben – bitte prüfen".
- **Medical boundary:** medical fields are never derived or paraphrased. The only medical content taken from a
  document is the **verbatim** main diagnosis for PAL 080 §3 "Leiden" (`document.main_diagnosis`, extracted by regex
  in `documents/facts.py`, quote + page, unconfirmed — the person checks it); Lotsi adds the secondary diagnoses
  verbatim on request. Other document prefills are administrative: hospital stay (§5 Krankenanstalt = ja, KH bis =
  discharge date) and the attachment "Kopie des Entlassungsbefunds".
- **Lebenslage "zu Hause mit Unterstützung"** (active `home_care` episode, no active stationary stay): PAL 080
  "Betreuung durch andere Person" = ja (`situation.home_care.any`) and "vorübergehender Aufenthaltsort" stays empty
  (`situation.home_care.temp_stay` + `blank_from_prefill`); neither is asked again. Without that episode both are asked.
- **Doctor-only:** `doctor_only_pages` blocks every AcroForm field whose widgets lie only on those pages
  (Kur/Reha p. 2 "Ärztliche Stellungnahme"); such fields are never prefilled, never asked, PATCH → 422, and are dropped
  at render even if a session was tampered with. Header fields shared with page 1 (VSNR) stay writable.
- Answers to questions that no longer apply (e.g. `Hausbesuch` switched back to "nein") are not rendered.

## Forms
| form_id | Mapping | Notes |
|---|---|---|
| `pva_pflegegeld_pal080` | 94 schema fields → all 97 AcroForm fields | §1–§11, §2 = actor (Maria) via delegation |
| `fsw_foerderung` | 119 fields → all 122 AcroForm fields except 3 signature fields | Pflege und Betreuung path prefilled; Behinderung/Obdach mapped too |
| `sv_kur_reha` | page 1: all 44 fields; page 2: 47 fields doctor-only | 4 doctor fields shown read-only |
| `oegk_fahrtkosten_wien` | all 13 fields | SVNR/IBAN normalised for comb fields |
| `oegk_rezeptgebuehr_befreiung` | 67 schema fields → all 68 AcroForm fields | ÖGK-KSLS/0088-01/V01, downloaded from oegk.at (see Sources). Prefilled: name, SVNR (comb, 10 digits), Straße + Nr., PLZ, Ort, Telefon, E-Mail (profile), Familienstand (profile, e.g. Anna = verwitwet), „Pension oder Rente“ amount (`facts.net_income_monthly`), Vermerke = who files it (delegation, proxy only), Ort/Datum. Never prefilled: income-type ticks, household members, package count. No consent boxes on this form (declarations = signature) |

Not mapped yet: `fsw_einrichtungswunsch`, `fsw_senioren_wg`, `sv_reha_nach_unfall` (hospital-filled, info only).

## Sources
Official AcroForm templates in `knowledge/forms/templates/` (field names + states verified against the PDFs). All
come from the challenge data (`docs/`) except `oegk_rezeptgebuehr_befreiung.pdf`: downloaded on 2026-11-06 from
https://www.oegk.at/cdscontent/load?contentid=10008.785277&version=1779440677 (info page
https://www.oegk.at/cdscontent/?contentid=10007.870471&portal=oegkportal), committed as-is; its fields.json is
re-dumped by `tools/extract/forms.py --downloaded-only` and MANIFEST entry `form_templates_downloaded` records URL,
date and sha256;
start, preview and render cite the form version in the audit log (`ctx.cite`). Prefill sources: demo profile
(labelled ID Austria / ZMR / e-card / Profilangaben), delegation, document quote + page, Lebenslage episode.

## Limitations
- **„Pflichtangaben“ are our classification, not the form's.** The official PAL 080 marks no individual required
  fields; its declaration says „Ich habe alle Fragen richtig und vollständig beantwortet“. We require 13 core fields
  (identity, address, Antragsart, Krankheiten) plus follow-ups once a yes/no question is „ja“; the yes/no questions of
  §4–§9 are `recommended`. So 100 % progress ≠ every question of the paper form answered. The wizard says so under
  the progress bar. Deliberate simplification for the demo (user decision, 06.11.2026); production: make the yes/no
  questions required and prefill them from Lebenslage/documents where known.
- PAL080 "Antragsart" defaults to "Zuerkennung / Erhöhung" (unconfirmed suggestion) to keep the demo session short;
  Yes/No sections (§4–§9) are `recommended`, not required, for the same reason (Lotsi offers them via
  `next-questions?include_optional=true`). KH von / Spital are asked (KH von only for the admission date; KH bis comes from the letter): the letter has no
  admission date or hospital name.
- No IBAN checksum / SVNR check digit validation. Text is not wrapped inside a single line; very long values shrink
  (auto font size) in viewers.
- Document prefill reads `store('document_analyses')`; the document must have been analysed first.
- Rezeptgebühr form: `facts.net_income_monthly` goes into the „Pension oder Rente“ row only (the facts store has no
  income type). The person ticks the income type; if the income is a salary, the amount must be moved in the review.
  „Vermerke“ is read as the applicant's own remark line (section 4, above the signature), not as office use.

## Tests
`app/services/forms/tests/test_forms.py` — schema sync, every `pdf_field` exists, full AcroForm coverage, radio export
states exist in the PDF, doctor-only enforcement, Maria→Anna prefill, document prefill, HTTP session flow + 422,
render read-back with pypdf, preview. `test_prefill_facts.py` — document facts (discharge date, verbatim diagnosis)
with quote + page. `test_prefill_situation.py` — Lebenslage prefill vs. document fallback, no mixing, scope check.
`test_lebenslage_prefill_home.py` — home care prefills "Betreuung" and the known-empty temporary stay.
`test_rezeptgebuehr_form.py` — definition + benefit link, Maria→Anna prefill with sources, no checkbox ticked by
prefill, stated income → pension amount with source, household rows follow „lebt allein“ (chained), render read-back
with draft stamp, number validation.
Run `make test-api`.
