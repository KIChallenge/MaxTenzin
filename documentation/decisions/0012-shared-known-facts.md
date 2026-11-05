# 0012 Shared known facts between cockpit and Lotsi
**Context:** Eligibility needs facts (care hours, income, household …). Asking the same question again in the chat after it was answered in the cockpit (or vice versa) is the opposite of a navigator.

**Decision:** Answers are stored per subject via `PATCH /api/benefits/facts` with provenance "Angabe von <Name>, <Datum> (Cockpit|Lotsi)". Every eligibility check merges them (request facts win; Lebenslage facts only with `manage_situation`). Lotsi loads them into its working memo before each turn and never asks them again.

**Consequence:** One source of truth for what the person has told the system, visible with provenance. Known limitation: the agent reads the stored document directly instead of via `GET /api/benefits/facts`.
