# appointments (WS-T)

## Purpose
"Termine suchen, vorbereiten und vereinbaren": find providers by topic and proximity, search free slots by the
person's preferences (near home, vormittags/nachmittags, barrierefrei), book a slot with an administrative
"Mitbringen" checklist, link it to a Mein-Fall step, cancel, and export it as an `.ics` calendar file.
All slots are **synthetic demo slots** (`demo: true`, `notice_de`): nothing is transmitted to a real practice.

## Endpoints (`/api/appointments`)
| Method | Path | Scope | What |
|---|---|---|---|
| GET | `/providers?topic=&zip=` | any authenticated | providers matching a topic, sorted by proximity (default zip = subject's address) |
| POST | `/slots/search` | `manage_appointments` | `SlotSearch` → free `Slot`s, near first, max 2 per provider |
| POST | `` | `manage_appointments` | `BookingRequest` → `Appointment` (409 if no longer free) |
| GET | `` | `manage_appointments` | appointments of the current subject |
| POST | `/{id}/cancel` | `manage_appointments` | status → `cancelled`, slot becomes free again |
| GET | `/{id}/ics` | `manage_appointments` | `text/calendar` (VEVENT, TZID Europe/Vienna) |

Appointments are subject-scoped (store collection `appointments`); another subject's id → 404.

## Rules & knowledge
- `knowledge/providers.yaml`: real facilities (`demo: false`, name/address/phone + `SourceRef`) and synthetic demo
  practices (`demo: true`, fictional names ending in "(Demo)"). `topics` = benefit / prevention ids + tags
  (`hausarzt`, `hausarzt_kontrolle`, `darmkrebs_vorsorge`, `koloskopie`, `impfung`, `ernaehrungsberatung` …);
  aliases are normalised (`vu`→`vorsorgeuntersuchung`, `darmkrebs`→`darmkrebs_vorsorge`, `grippe`→`influenza` …).
- Slot generator (`service.py`): weekday opening hours per provider kind (overridable per provider), 20-min slots
  (GP, Gesundheitszentrum, Impfstelle) or 30-min (Fachärzt:in, Beratung, Reha); an "already booked" mask from
  `random.Random("<provider_id>:<date>")` (≈45 % taken) → identical results across runs; never in the past
  (`service.now` is injectable); search window 21 days from `from_date` (default: tomorrow).
- Filters: `topic`, `kind`, `specialty` (case-insensitive substring), `daypart` (morning < 12:00 ≤ afternoon),
  `accessible_only`. `near=true` ranks: same district → neighbouring district (Vienna adjacency map) → other
  Vienna districts → outside Vienna (PLZ difference); then by start time. `distance_hint_de` e.g.
  "im selben Bezirk (1030)", "im Nachbarbezirk (1040 Wieden)".
- Booking re-validates the slot under a lock (exists in generator, future, not masked, not booked) → else 409.
- `bring_documents_de` = defaults ∪ request list: always `e-card`; `Entlassungsbrief (Kopie)` for post-discharge
  control / Reha / Nachsorge; `Impfpass` for vaccinations; `Überweisung/Zuweisung (falls vorhanden)` for
  specialists; `Vollmacht bzw. Nachweis der Vertretung` when actor ≠ subject. The topic is taken from the linked
  Mein-Fall step (`benefit_id`, else title keywords) and the provider kind.
- Mein-Fall link: with `case_id` (+ `step_id`) the case is first read via `GET /api/cases/{id}` with the user's own
  token (so `manage_case` applies; 403/404 propagate, nothing is booked), then after booking an `open` step is set
  to `in_progress` via `PATCH /api/cases/{id}/steps/{step_id}`. No import of cases internals.
- Medical boundary: `purpose_de` is stored as given (the person's own words / administrative purpose, max 300
  chars). The service adds no medical content; checklists are purely administrative.
- Audit: real providers' sources are cited via `ctx.cite`, rule id `appointments.demo_slots.v1`.

## Sources
- ÖGK Serviceratgeber 2026, S. 89–92 (Gesundheitszentren, Physikalische Medizin) and S. 94–96 (Wiener addresses).
- PAL 080, S. 8 (PVA Landesstelle Wien – Kundenzone); FSW Antrag auf Förderung von Leistungen, S. 1 (FSW).

## Limitations
- Slots, opening hours and "already booked" are synthetic; real facilities get demo slots too (labelled).
- Per-site offers of the ÖGK Gesundheitszentren (S. 90 table) are not machine-readable → only "Vorsorgeuntersuchung".
- Preferences (`daypart`, `near_home`, `accessible`) are not read server-side yet: the caller (Lotsi/UI) passes them.
- Wien only for demo practices; outside Vienna proximity is a plain PLZ difference.

## Tests
`app/services/appointments/tests/test_appointments.py` — providers sourced/labelled, reproducible slots, default
from_date, daypart filter, near ordering for Anna (1030), filters, booking + 409 + cancel re-frees, masked/past/
unknown slots, subject isolation, ICS validity (folding, escaping, TZID), case-step link, scopes (Maria→Anna ok,
Stefan→Anna 403, revoked `manage_appointments` 403).
