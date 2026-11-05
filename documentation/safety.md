# Safety, consent and honesty

How the prototype keeps the AI inside defined processes. Each rule names the code that enforces it; mechanisms are
deterministic unless stated otherwise. Architecture context: [architecture.md](architecture.md).

## 1. Medical boundary
Lotsi is a navigator for social insurance, not a medical advisor (CLAUDE.md invariants 6 and 8).

| Refused (fixed template, no tool call, < 0.2 s) | Allowed |
|---|---|
| Making a diagnosis ("Was hat meine Mutter?", "Ist das Krebs?") | Naming recommendations a document states **explicitly**, each with verbatim quote + page |
| Interpreting findings, images, lab values ("Was bedeutet der Röntgenbefund?") | Copying documented diagnoses **verbatim** into a form field that asks for them (PAL 080 "Krankheiten bzw. Beeinträchtigungen"), unconfirmed, with quote + page |
| Prognosis, personal risk ("Wie hoch ist ihr Rückfallrisiko?") | Explaining official prevention programmes (e.g. Koloskopie ab 45) incl. family history — never risk numbers, always "entscheidet Ihre Ärztin bzw. Ihr Arzt" |
| Medication, dosing, therapy advice | Administrative EKO facts: box, approval requirement, Rezeptgebühr |
| Filling doctor-only sections (Kur/Reha p. 2 "Ärztliche Stellungnahme") | Preparing the parts the person fills in; saying who completes the rest |
| Role play as a doctor | Preparing an appointment, questions for the doctor, finding the responsible office |
| Emergencies / suicidality → 144, 1450, Telefonseelsorge 142 | — |

Enforcement layers:
1. **Input guard** (`agent/guard.py:check_boundary`): regex intent patterns (DE/EN/TR) run before any LLM or tool
   call. Two deterministic exemptions run before the optional LLM check: `is_copy_request` (copy/enter + diagnosis/
   letter, no interpretation words like "bedeutet", "heilbar", "Prognose") and `is_prevention_programme_question`
   (Vorsorge/Impfung/Screening, no personal-risk phrasing). In live mode, other messages with health vocabulary get a
   small LLM classification; it can only add a refusal.
2. **Documents** (`documents/extract.py`): imaging reports and vaccination records never yield recommendations (+ notice
   "Ich interpretiere keine Befunde …"); a deterministic CLINICAL filter removes instructions to physicians (labs, blood
   pressure, medication, side effects, fluid balance) even when quoted verbatim, and says so in a notice.
3. **Diagnosis copy** (`documents/facts.py`, `forms/prefill.py`, `orchestrator.py:_copy_diagnoses`): main/secondary
   diagnoses are taken by regex, verbatim, with quote + page — never summarised by the model. PAL 080 `Leiden` is
   prefilled *unconfirmed*; on an explicit copy request Lotsi writes the verbatim text deterministically.
4. **Prevention wording** (`prevention/engine.py`, output guard): "laut Impfplan empfohlen" / "nicht im e-Impfpass
   dokumentiert – bitte mit Ärztin/Arzt klären"; "Ihnen fehlt …" is rejected.
5. **Evals**: 20 boundary/red-team cases incl. prompt injection (in the message and in an uploaded PDF), EN and TR —
   34/34 live ([evals/REPORT.md](../evals/REPORT.md)).

## 2. Consent
- **Nothing is ever submitted.** Forms end as the official PDF stamped "ENTWURF – bitte prüfen und selbst
  unterschreiben" (`forms/pdf.py`). Submission requests hit the input guard (`submit`); the output guard rejects
  replies claiming something was "eingereicht/abgeschickt/übermittelt".
- **Consent checkboxes are never ticked by the agent.** `ToolClient.run` returns 422 if `set_form_fields` would set a
  checkbox whose label contains Zustimmung/Einverständnis/Einwilligung; the reply then lists them under "Noch offen –
  bitte im Antrag selbst ankreuzen". Model sentences claiming a consent was set are removed. A *choice* the person
  explicitly asks for (e.g. Pflegeberatung = Ja) is entered.
- **Lebenslage suggestions need explicit consent.** Documents only create suggestions (`status: suggested`, quote +
  page); they have no effect (no facts, reminders, prefill or case steps) until `POST …/suggestions/{id}/confirm`. In
  the cockpit that is the button "Ja, übernehmen"; Lotsi may call `confirm_situation_suggestion` only if the same
  message contains an explicit yes (`_CONSENT_YES`) — otherwise a deterministic 422. Rejected suggestions are never
  re-suggested.
- **Bookings** happen only after the person picks a slot; slots are labelled demo slots.
- **Writes are stated, not claimed.** After a successful `set_form_fields`, the reply begins with a deterministic
  "Eingetragen im Antrag: <Label> = <Wert>" built from the tool result; "eingetragen/halte fest" without a successful
  write triggers a retry with tools.

## 3. Delegation and scopes
Mock ID Austria: token `demo-<persona>` = actor, `X-Subject-Id` = person acted for. Acting for oneself = all scopes;
for someone else = exactly the delegation's scopes (`app/core/auth.py`). **The AI inherits** them: Lotsi calls every
endpoint with the user's own token; a 403 is explained ("Dafür hat <Name> keine Berechtigung erteilt …") and never
worked around. Only the grantor can extend scopes; changes persist in the store (`delegation_overrides`).

| Scope | Cockpit label | Demo: Maria → Anna | Demo: Stefan → Lena (Obsorge) |
|---|---|---|---|
| `read_documents` | Dokumente lesen | ✅ | ✅ |
| `prepare_applications` | Anträge vorbereiten | ✅ (revoked live in Akt 3) | ✅ |
| `manage_appointments` | Termine verwalten | ✅ | ✅ |
| `view_health_prevention` | Vorsorge- und Gesundheitsdaten einsehen | ❌ deliberately not granted | ✅ |
| `manage_case` | Fall verwalten | ✅ | ✅ |
| `manage_situation` | Lebenslage | ✅ | ✅ |

Scopes apply transitively to composed endpoints (inbox, situation → cases, appointments → cases): those call the other
services over HTTP with the same token. Full endpoint/scope table: [services.md](services.md).

## 4. Audit and transparency
- Every API call — cockpit, Lotsi, or service-to-service — is one audit row: actor, subject, `via`
  (`ui`/`agent`/`service:<name>`), agent tool, path, status, required scope, allowed, cited sources, rule ids
  (`core/audit.py`). Denied calls are logged with `allowed=false`. The Transparenz page shows them, denied ones in red.
- Each chat reply carries a `tool_trace` (tool, arguments, status, one-line German summary, sources).
- Shared facts carry provenance "Angabe von <Name>, <Datum> (Cockpit|Lotsi)"; episodes "Angabe von …" or the document
  quote; care-team entries "Profil (Demo) – im Echtbetrieb aus e-card-Konsultationen" or "Angabe von …".

## 5. Honesty measures
- **Every fact has a `SourceRef`**: law § with in-force date, veraendW table + year, Serviceratgeber page (quotes
  checked verbatim at load time), official form page, document quote + page, or external web page with retrieval
  date. Legal information is labelled "unverbindliche Information, keine Rechtsberatung"; eligibility ends with
  "Unverbindliche Information – die Entscheidung trifft …".
- **Amounts** only from tool data (output guard); veraendW first — § 5 BPGG still shows 2020 amounts.
- **Prefill provenance is honest** (`forms/prefill.py`): "ID Austria (Demo)" only for name and birth date; "ID Austria –
  Hauptwohnsitz laut ZMR" for the address; "e-card / Sozialversicherung" for SVNR and insurer; everything else
  "Profilangaben – bitte prüfen". All prefills start `confirmed: false`.
- **Demo labels**: appointment slots and demo practices ("(Demo)", `demo: true`, notice), care team "Profil (Demo)",
  personas and documents are fictional.
- **Photos**: "Aus einem Foto gelesen – bitte prüfen Sie die übernommenen Angaben" plus a low-resolution notice below
  1400 px; the cockpit shows "Was Lotsi gelesen hat" (`/api/documents/{id}/transcript`).
- **Internal ids are never shown**: session UUIDs, `*_id` lines, `demo-…` ids and tool names are stripped from replies.

## 6. Known limitations
- **Photo quotes are verified against the model's own transcription**, not the paper: a misread word that the
  extractor then quotes passes verification. Hence the notice and unconfirmed status.
- The input guard is regex-based and can be phrased around; the LLM double-check (live only) and the system prompt are
  the second and third lines. False positives are possible; the refusal always offers an administrative alternative.
- The output guard checks amounts, submission/write/consent claims, prevention wording and question count — not every
  factual sentence.
- Live extraction varies between runs (every item is still quote-verified); the first live result per file is cached
  so a demo shows a stable analysis.
- The Impfplan intervals were taken from the brief and not re-verified against the current Impfplan PDF; risk groups
  are not modelled.
- Mock identity: no real ID Austria, no e-Vollmacht, no real e-card data. Single-node SQLite; not hardened for
  production (no rate limiting, no encryption at rest). See [roadmap.md](roadmap.md).
