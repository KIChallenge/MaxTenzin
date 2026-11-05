# prevention

**Purpose.** Reads e-Impfpass entries and shows vaccination and screening hints for a person. Everything is deterministic and sourced, with no LLM. Wording follows invariant 8: "laut Impfplan empfohlen" and "nicht im e-Impfpass dokumentiert – bitte mit Ihrer Ärztin bzw. Ihrem Arzt klären". It never says "fehlt".

## Endpoints (`/api/prevention`, scope `view_health_prevention`)
| Method | Path | |
|---|---|---|
| GET | `/overview?as_of=YYYY-MM-DD` | Stored vaccinations plus `PreventionItem`s. `as_of` defaults to today. Without an import, every vaccination is `not_documented` |
| POST | `/import/{document_id}?as_of=` | Parses an uploaded e-Impfpass (422 if the document is not one or has no entries) and stores the result in collection `vaccinations` (key = subject id). The demo id `doc-stefan-impfpass` works without an upload, via its golden |

## Rules & knowledge — `knowledge/prevention.yaml`
| id | logic | source |
|---|---|---|
| influenza | seasonal (dose since Sep → up_to_date; Oct–Mar otherwise due) | Impfplan (external) + SR S. 32 |
| covid19 (≥60) | seasonal | Impfplan (external) + SR S. 32 |
| dtp_polio | interval 10 y (≥60: 5 y); due / upcoming (≤1 y) / up_to_date | Impfplan (external) + SR S. 32 |
| herpes_zoster, pneumococcal (≥60) | info (kostenlos ab 60) | SR S. 32 |
| fsme | info (Kostenzuschuss) | SR S. 32 |
| kinderimpfprogramm (<18) | info | SR S. 32 |
| vu (≥18) | annual screening → due | SR S. 23 |
| darmkrebs (≥45) | screening → due | SR S. 24 |
| mammografie (w, ≥40) | 45–74 due; 40–44 upcoming; ≥75 opt-in info | SR S. 25 |

Brochure sources carry a verbatim quote; a test checks each one against `knowledge/extracted/serviceratgeber/pages.jsonl`. External sources (Impfplan Österreich 2025/2026) are `kind: external`, with the URL in `ref` and "abgerufen am 05.11.2026" in the label.

## e-Impfpass parser (`impfpass.py`)
Line-based parsing of the ELGA e-Impfpass PDF export: disease heading → date line → `Impfstoff:` → `Impfdatum:` (the full date wins) → dose label → `Impfort:` + zip/city. Combined vaccines ("Diphtherie, Tetanus, …") become `Diphtherie-Tetanus-Pertussis-Polio`. Batch numbers, PZN and doctor names are deliberately not stored.

## Goldens
- `evals/goldens/da2002….json` (`vaccinations`): Stefan's e-Impfpass, 9 entries.
- `evals/goldens/prevention_stefan_2026-11-05.json`: influenza due (last 2025-11-03), dtp_polio not_documented, fsme not_documented, vu due.

## Limitations
- The Impfplan intervals come from the WS-D brief and were **not** re-verified against the current Impfplan PDF. Risk groups are not modelled, because that would be a medical assessment. COVID-19 is shown only from age 60.
- Screening history is not available, so screenings are "possible/due" by age alone.
- Zoster, pneumococcal and FSME are info only: no dose-schedule logic.

## Tests
`app/services/prevention/tests/test_prevention.py`: parser, Stefan and Anna goldens, seasonal and interval logic, the wording rule (no "fehl…"), external-source marking, brochure quotes verbatim, endpoints including scope denial.
