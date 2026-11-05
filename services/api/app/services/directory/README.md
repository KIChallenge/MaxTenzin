# directory

## Purpose
"Wer ist zuständig?" — responsible offices by topic (benefit id or generic tag) and nearest by postcode.

## Endpoints
`GET /api/directory/offices?topic=&zip=&provider=&limit=` → `list[Office]` (each with `source`).

## Rules & knowledge
- `knowledge/offices.yaml`: ÖGK Wien Kundenservicestellen + Gesundheitszentren, PVA Landesstellen (all 9 + Kundenzone
  Wien), FSW Kund:innenservice, 1450. Topics = benefit ids from `knowledge/benefits.yaml` + generic tags.
- Ranking with `zip`: Vienna → distance between approximate district centroids (ordering only, never shown);
  elsewhere → same Bundesland digit first, then numeric postcode distance; nationwide services (no zip) last.

## Sources
ÖGK Serviceratgeber 2026 S. 82, 94–96; PAL 080 S. 8; FSW Antrag auf Förderung S. 1.

## Limitations
ÖGK offices outside Vienna are not yet listed (Serviceratgeber S. 96–115 has them). Finanzamt (Familienbeihilfe) is
not in our sources.

## Tests
`app/services/directory/tests/test_directory.py`
