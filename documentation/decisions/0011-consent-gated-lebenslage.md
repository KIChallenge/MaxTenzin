# 0011 Lebenslage suggestions from documents take effect only after consent
**Context:** A discharge letter implies a hospital stay, home care, therapy or planned Reha. These episodes drive deadlines, eligibility facts, prefill and case steps — consequential, and possibly wrong if read from a photo.

**Decision:** Documents create only `suggested` episodes with quote + page (deterministic rules, no diagnosis content). They have no effect until `POST /api/situation/suggestions/{id}/confirm` (cockpit "Ja, übernehmen"; Lotsi only with an explicit yes in the same message, deterministic 422 otherwise). Rejected suggestions stay rejected.

**Consequence:** Effects (Meldepflicht reminder, facts, PAL 080 §5 prefill, Mein-Fall steps) always rest on a confirmed episode with a named source. The person stays in control of what the system believes about their situation.
