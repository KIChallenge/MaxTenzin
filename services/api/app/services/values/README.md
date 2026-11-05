# values

## Purpose
Yearly amounts (veränderliche Werte) from veraendW — the only source for amounts (CLAUDE.md invariant 3).

## Endpoints
- `GET /api/values/{key}?year=2026` → `Value` · `GET /api/values?year=2026` → `list[Value]`

## Rules & knowledge
`service.py` (`get_value`, `require_value`, `value_source`) is shared with benefits and medications.

## Sources
`knowledge/extracted/values/veraendw.json` (Tab. 20, 25, 46, 53, 54).

## Limitations
Only mapped keys; Familienbeihilfe amounts and Fahrtkosten (Satzung) are not in veraendW.

## Tests
`app/services/values/tests/test_values.py`
