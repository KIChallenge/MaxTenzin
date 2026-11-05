# WS-F — Forms: one schema, two clients (wizard + chat), real PDF fill

> **Historical brief** — the task as handed to the workstream at the start. Current behaviour: the service READMEs, `documentation/architecture.md` and `documentation/services.md`.

**Branch:** `ws/F-forms` · **Owned paths:** `services/api/app/services/forms/`, `knowledge/forms/*.yaml`, `knowledge/schema/form.schema.json`
Read `CLAUDE.md` first. Contract: `app/contracts/forms.py` — don't change (Contract requests in PROGRESS.md).

## Inputs (committed)
`knowledge/forms/templates/<form_id>.pdf` + `<form_id>.fields.json` (AcroForm field names/types/states + page text):
`pva_pflegegeld_pal080` (102 fields), `fsw_foerderung` (122), `sv_kur_reha` (96, page 2 = doctor-only), `oegk_fahrtkosten_wien` (13), `fsw_einrichtungswunsch` (13), `fsw_senioren_wg` (21), `sv_reha_nach_unfall` (59, hospital-filled → info only).

## Tasks
- [ ] Form schema YAML per form (`knowledge/forms/<form_id>.yaml`): sections, fields mapped to real AcroForm names (`pdf_field`, `pdf_on_value` for checkboxes — read states from fields.json), `label_de`, `type`, `required`, `ask_hint_de` (plain-language question), `prefill` rule (`profile.<path>` | `actor.<path>` | `document.<key>` | `delegation.<key>` | constant), `doctor_only: true` → readonly with `readonly_reason_de`. Priority: PAL080 (all patient fields incl. §2 Antragstellung durch andere Person = Maria, §3 Leiden, §4 Betreuung/mobile Dienste, §5 Krankenhausaufenthalt, §9 Pflegeberatung consent, §11 Unterlagen), then FSW Förderung (Pflege und Betreuung path), then Kur/Reha p.1, then Fahrtkosten.
- [ ] Prefill engine: person profile (contract `Person`), actor (for "andere Person"), delegation (relation), document analysis (e.g. hospital stay dates, Leiden only as verbatim quotes from the document — never paraphrase medical content), each `FieldValue` with `SourceRef`.
- [ ] Sessions persisted in `store` ("form_sessions"), real uuid ids; `next-questions` = required & empty & not doctor_only, ordered by section; `PATCH` validates types/options (422 on bad input, German message).
- [ ] Render: fill the official PDF with pypdf (`update_page_form_field_values`, keep NeedAppearances), add a small "ENTWURF – bitte prüfen und selbst unterschreiben" stamp/watermark, return as download; also `GET /sessions/{id}/preview` → JSON list of (label, value, source) for the review step.
- [ ] Endpoints keep signatures; definitions served from YAML (not fixtures).
- [ ] Tests: schema validation of all YAMLs against form.schema.json; every `pdf_field` exists in fields.json; prefill for Maria→Anna fills name/geburtsdatum/address/§2; render produces a PDF whose fields contain the values (read back with pypdf); doctor-only fields never writable.
- [ ] per-service README.md.

## Definition of Done
`make test-api` + `make lint` green; PAL080 + FSW fully mapped; rendered PAL080 opens with values in Preview/Acrobat; PROGRESS.md row updated; commits on `ws/F-forms`.
