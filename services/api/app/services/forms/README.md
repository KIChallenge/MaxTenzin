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
| POST | `/definitions/{form_id}/sessions?document_id=` | start a prefilled session (uuid id). `document_id` (optional, needs `read_documents`) adds non-medical facts from `store('document_analyses')` |
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
  `proxy`), `required` / `recommended`, `ask_hint_de`, `prefill`, `doctor_only` + `readonly_reason_de`.
- Prefill (`prefill.py`): `profile.*` (subject), `actor.*` + `delegation.*` (only when acting for someone else),
  `document.*`, `system.today`, `const:` (a suggestion, unconfirmed). Every prefill carries a `SourceRef` and starts
  `confirmed: false`.
- **Medical boundary:** medical fields (e.g. PAL080 §3 "Leiden", Medikamente) are never prefilled, derived or
  paraphrased; the person enters them (ideally copied verbatim from the Befund). From documents we only take the
  file name (Beilagen) and the fact that it is a discharge letter (§5 Krankenanstalt = ja).
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

Not mapped yet: `fsw_einrichtungswunsch`, `fsw_senioren_wg`, `sv_reha_nach_unfall` (hospital-filled, info only).

## Sources
Official AcroForm templates in `knowledge/forms/templates/` (field names + states verified against the PDFs);
start, preview and render cite the form version in the audit log (`ctx.cite`). Prefill sources: ID Austria demo profile, delegation, document.

## Limitations
- PAL080 "Antragsart" defaults to "Zuerkennung / Erhöhung" (unconfirmed suggestion) so the demo session has only
  "Leiden" left as a required question; Yes/No sections (§4–§9) are `recommended`, not required, for the same reason.
- No IBAN checksum / SVNR check digit validation. Text is not wrapped inside a single line; very long values shrink
  (auto font size) in viewers.
- Document prefill reads `store('document_analyses')`; the document must have been analysed first.

## Tests
`app/services/forms/tests/test_forms.py` — schema sync, every `pdf_field` exists, full AcroForm coverage, radio export
states exist in the PDF, doctor-only enforcement, Maria→Anna prefill, document prefill, HTTP session flow + 422,
render read-back with pypdf, preview. Run `make test-api`.
