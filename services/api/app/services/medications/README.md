# medications

## Purpose
Administrative Erstattungskodex (EKO) lookup: box, approval requirements, patient cost (Rezeptgebühr vs. price).
Never dosing, therapy or substitution advice (CLAUDE.md invariant 6).

## Endpoints
- `GET /api/medications/search?q=&limit=` → `list[Medication]` (prefix matches first).
- `GET /api/medications/{pharma_nr}` → `Medication` (1–7 digits, zero-padded; 404 if unknown).

## Rules & knowledge
Restriction codes → plain administrative German (RE1/RE2/IND/F14/F6J/F2J, codes per EKO legend); unknown codes are
named, not interpreted. Cost note uses the Rezeptgebühr from veraendW 2026.

## Sources
`knowledge/extracted/eko/medications.jsonl`, `legend.json`; veraendW Tab. 20.

## Limitations
Codes such as `N`, `P`, `Au`, `D`, `U` are shown as "Weitere Einschränkung" without explanation (not in legend).

## Tests
`app/services/medications/tests/test_medications.py`
