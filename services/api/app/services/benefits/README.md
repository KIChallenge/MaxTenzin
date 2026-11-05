# benefits

## Purpose
Benefit catalog (Leistungen + Angebote), deterministic eligibility ("kommt voraussichtlich in Frage") and situation
bundles ("Bündel"). No LLM. Every criterion carries a `SourceRef`; every amount comes from veraendW (values service)
or, where no value table exists, from the cited rule text (Satzung ÖGK § 46 Abs. 5 Fahrtkosten, RRZ § 13 Abs. 1a
Obergrenze) or the verbatim brochure sentence (Heilbehelfe/Hilfsmittel, Serviceratgeber 2026 S. 45–46).

## Endpoints
| Method | Path | Notes |
|---|---|---|
| GET | `/api/benefits?area=A..F&kind=benefit\|offer` | catalog (order of `knowledge/benefits.yaml`, `pflegegeld` first); offers have ids `angebot_*` |
| GET | `/api/benefits/{id}` | one benefit incl. `legal_basis` (with in-force date) and `sources` |
| POST | `/api/benefits/eligibility` | `EligibilityRequest` → `list[EligibilityResult]` (catalog order). Without `benefit_ids` offers are left out; request them by id or via bundles |
| GET | `/api/benefits/rezeptgebuehr/check?net_income_monthly=&household=alleinstehend\|paar&children_count=&chronic_illness_expenses=&receives_ausgleichszulage=` | calculator → results for `rezeptgebuehrenbefreiung` + `rezeptgebuehrenobergrenze` |
| GET | `/api/benefits/bundles/catalog` | all 5 bundles, evaluated for the current person without facts |
| POST | `/api/benefits/bundles/match` | `BundleRequest` {`situation` id \| `text`, `facts`, `document_ids`} → `Bundle` or `null` (text matches nothing). Unknown id → 404; neither → 422; only `document_ids` → `nach_spital` |

`subject_id` must equal the acting context (`X-Subject-Id`), else 403. `document_ids` need scope `read_documents`;
analyses are read from store collection `document_analyses` (WS-D), fallback: golden `doc-anna-entlassung` for Anna.

### Facts the engine understands (`facts`, all optional — missing ones appear in `missing_fields`)
| key | type | used by |
|---|---|---|
| `care_need_months`, `care_hours_estimate` | number | pflegegeld (Stufe estimate from BPGG § 4 Abs. 2) |
| `receives_pflegegeld`, `pflegegeld_applied` | bool | pflegeberatung, pflegekarenzgeld |
| `care_need_at_home` | bool | fsw_mobile_pflege |
| `home_nursing_ordered` | bool | hauskrankenpflege |
| `reha_application_with_medical_statement`, `gross_income_monthly` | bool, number | reha_onko (Zuzahlung tier) |
| `walking_unable_confirmed` | bool | krankentransport |
| `treatment_type` | `strahlentherapie\|chemotherapie\|immuntherapie\|dialyse\|…` | krankentransport, fahrtkostenzuschuss |
| `distance_km`, `treatment_outside_home_town`, `companion_needed` | number, bool, bool | fahrtkostenzuschuss |
| `rgb_exempt` | bool (already befreit wegen sozialer Schutzbedürftigkeit) | fahrtkostenzuschuss, krankentransport, heilbehelfe_hilfsmittel (Kostenanteil 0) |
| `net_income_monthly`, `household` (`alleinstehend\|paar`), `lives_alone`, `children_count`, `chronic_illness_expenses`, `receives_ausgleichszulage` | | rezeptgebuehren* |
| `costs_eur` | number | unterstuetzungsfonds |
| `familienbeihilfe_received`, `shared_household_with_child` | bool | familienbeihilfe, kinderbetreuungsgeld |
| `aid_needed`, `aid_type`, `aid_prescribed` | bool, text (e.g. "Rollator"), bool | heilbehelfe_hilfsmittel — e.g. Anna: letter p.3 "Kurze Gehstrecken mit Rollator möglich" → the agent passes `aid_needed: true, aid_type: "Rollator"` (the engine never parses medical text) |
| `pflegegeld_level` | int 0–7 (current Stufe of the person cared for; 0 = none) | ersatzpflege, foerderung_24h_betreuung, selbstversicherung_pflege, pflegekarenzgeld |
| `dementia_documented` | bool (explicitly stated) | ersatzpflege (Stufe 1 suffices) |
| `main_carer_since_months`, `carer_prevented` | number, bool | ersatzpflege |
| `care_24h_needed`, `care_24h_carer_qualified` | bool, bool | foerderung_24h_betreuung |
| `pflegekarenz_agreed`, `caregiver_insured_3m` | bool, bool (about the caring relative) | pflegekarenzgeld |
| `caregiver_main_carer` | bool | selbstversicherung_pflege |
| `financial_hardship` | bool | sozialhilfe_wien |
| `in_employment`, `diabetes_type2`, `pregnant`, `young_child` | bool | offers (Jugendlichenuntersuchung, Therapie Aktiv, Richtig essen — `young_child` is derived from the children in Obsorge if not given) |
| `family_history` | list (`darmkrebs`, `brustkrebs`, `diabetes`, `herz_kreislauf`, aliases) | bundles → prevention engine ("besonders relevant") |
| `recommendations` (+ `document_filename`) | list of `Recommendation` | alternative to `document_ids` |
| `as_of` | ISO date | age computations (tests/demo) |

Household is also derived from the document (`ExtractedPerson.living_situation` containing "allein").
Family benefits: if the subject is a minor they are evaluated for the subject; for adults, for the youngest child
in their Obsorge (delegations with relation "Obsorge"). Carer benefits (Ersatzpflege, Pflegekarenzgeld,
Selbstversicherung) are evaluated in the context of the person cared for; facts about the caring relative are passed
explicitly.

### Shared known facts (`/api/benefits/facts`, store collection `known_facts`)
| Method | Path | Notes |
|---|---|---|
| GET | `/api/benefits/facts` | facts answered so far for the subject + provenance per key |
| PATCH | `/api/benefits/facts` | `{"facts": {key: value}}` merge; `null` deletes; `recommendations`, `as_of`, `document_filename` are never stored |

Provenance label "Angabe von <Actor>, <TT.MM.JJJJ> (Cockpit|Lotsi)" (Lotsi = `X-Via: agent`). Every eligibility and
bundle evaluation merges them: request facts win over known facts, known facts win over Lebenslage facts
(`situation_facts`, only with `manage_situation`); audit rules `benefits.facts_known:<keys>` /
`benefits.facts_from_situation:<keys>`. Lotsi saves answers here and never asks a known fact again.

## Rules & knowledge
- `knowledge/benefits.yaml` (schema `knowledge/schema/benefits.schema.json`, generated from `catalog.py`):
  20 benefits + 13 offers (`kind: offer`), areas A Vorsorge · B Gesund werden · C Reha · D Pflege · E Kosten · F Familie.
- Source specs: `{law, nr, abs}` · `{page, quote?}` (quote is checked verbatim against the Serviceratgeber page at load
  time) · `{form, page, label}` · `{value}` · `{url, label, retrieved}` (external website, `kind: external`).
- `service.py`: one pure evaluator per benefit, `rule_ids = ["<benefit>.v1"]`; offers share `eval_offer` (data-driven:
  `of_open` always met, `of_age` by `offer.min_age/max_age`, `of_fact` by `offer.requires_fact`, `of_season` info).
- Status: any criterion `False` → `not_applicable`; all `True` → `likely`; else `needs_info`. Discretionary benefits
  without legal entitlement (reha_onko, unterstuetzungsfonds, family benefits, ersatzpflege, foerderung_24h_betreuung,
  sozialhilfe_wien, offers for Betriebe/Schulen/Vereine) are capped at `possible`. heilbehelfe_hilfsmittel is
  `possible` once the need is known (the prescription is the doctor's decision), `likely` with prescription.
- Every result ends with "Unverbindliche Information – die Entscheidung trifft …" (offers: "… Angebote und Termine
  können sich ändern; bitte beim Anbieter prüfen.").

### Situation bundles (`bundles.py`, `knowledge/bundles.yaml`)
| id | example text | content (curated order) |
|---|---|---|
| `pflege_zuhause` | „Meine Mutter braucht jetzt Hilfe, was muss ich denn da machen?" | Pflegegeld + PAL 080, Pflegeberatung, FSW + Förderantrag, Heilbehelfe/Hilfsmittel, Hauskrankenpflege, Beratungstermin, Ersatzpflege, 24-h-Förderung, Pflegekarenzgeld, Selbstversicherung, Trittsicher, Rezeptgebühr, nearest PVA office |
| `nach_spital` | „Ich habe einen Entlassungsbrief – was muss ich erledigen?" (or only `document_ids`) | Kontrolltermin, Hauskrankenpflege, FSW, Pflegegeld + PAL 080, Pflegeberatung, Reha + Antrag, Transport, Fahrtkosten, Hilfsmittel, Rezeptgebühr, ÖGK office |
| `gesundheit_foerdern` | „Ich möchte etwas für meine Gesundheit tun" | Vorsorgeuntersuchung + Termin, Darmkrebs/Mammografie/Impf items (prevention engine), Bewegt im Park, Gesunder Rücken, regionale Kurse/Ernährungsberatung, Richtig essen, Rauchfrei, Momente für mich, Bewusst leben +, Trittsicher, Therapie Aktiv (only with `diabetes_type2`), BGF, Gesundheitszentrum |
| `kind` | „Ich habe ein Kind …" | Eltern-Kind-Pass + Termin, Familienbeihilfe, KBG, Kinderimpfprogramm (if the subject is the child), Richtig essen, Gesunde Schule, Vereinscoaching, KBG office |
| `finanzielle_unterstuetzung` | „Ich kann mir die Rezeptgebühr nicht leisten" | Rezeptgebühr-Befreiung/-Obergrenze, Unterstützungsfonds, Hilfsmittel-Kostenanteil, Fahrtkosten, Pflegegeld, Mindestsicherung Wien, ÖGK office |

- Matching: lower-case + umlaut folding + punctuation removed; keyword matches at a word start; 3 points per strong,
  1 per weak keyword; highest wins, ties by file order; audit rule `bundles.match.text:<id>:<hits>`.
- Items: benefit/offer status from `service.evaluate` (same facts and document recommendations as `/eligibility`;
  a document recommendation becomes the item's source + "Im Dokument ausdrücklich empfohlen (Datei, S. x)");
  `not_applicable` items are dropped; prevention items need scope `view_health_prevention` (else skipped, audit
  `bundles.prevention_skipped_no_scope`); offices = nearest office by topic; forms only if the related benefit is not
  `not_applicable`. `questions_de` = up to 3 missing facts, ranked by the bundle's `questions` priority list.
- Load-time validation: every benefit/prevention/form/office ref and every source must resolve (`test_bundles.py`).

## Sources
SozDok paragraphs (BPGG incl. §§ 21a–21e, ASVG incl. §§ 18b, 137, 154, RRZ 2008, Satzung ÖGK 2025 incl. §§ 28, 43,
RUF 2020, RVU, FLAG, KBGG, MuKiPassV 2002, RRK 2021), veraendW 2026, ÖGK Serviceratgeber 2026 (S. 22–34, 43–46,
48–49, 63–64, 69–75, 85), form templates (PAL 080, FSW Förderantrag, ÖGK Fahrtkosten, Kur/Reha). External (retrieved
05.11.2026): Bewegt im Park (https://www.bewegt-im-park.at/ — "Alle Kurse sind kostenlos und ohne Anmeldung", Juni
bis September), Sozialinfo Wien – Mindestsicherung, MA 40 (wien.gv.at/sozialinfo …it_1=2102082).

## Limitations
- Familienbeihilfe amounts are not in veraendW → no amount shown. FSW has no law in the corpus → form sources only.
- The engine does not parse document quotes: medical facts (e.g. `treatment_type`, `aid_needed`, `dementia_documented`)
  must be passed as facts.
- Pflegegeld Stufe 5–7 depend on qualitative criteria; the estimate stops at Stufe 4.
- Heilbehelfe/Hilfsmittel amounts (46,20 € Mindestkostenanteil, 1.848,00 € Höchstbetrag) are cited from the
  Serviceratgeber 2026; Satzung §§ 28/43 define them as multiples of the Höchstbeitragsgrundlage, which is not in our
  veraendW extract. Pflegekarenz: the required Pflegegeld-Stufe is in AVRAG § 14c (not in the corpus) → not stated.
- Ersatzpflege / 24-h-Förderung / Mindestsicherung: no amounts (Richtlinien resp. Stadt Wien, not in our sources).
- Sozialministeriumservice and MA 40 have no office entry (address not in our sources); contacts are in the steps.
- Bewegt im Park: the website names no organiser, only funders; label says "gefördert u. a. vom Dachverband der
  Sozialversicherung". Bundles: wording-based matching only (no synonyms beyond the curated lists).

## Tests
`app/services/benefits/tests/`: catalog integrity + schema sync, Anna/Stefan/Lena goldens, Rezeptgebühr calculator,
`test_catalog_k2.py` (new benefits, offers, external sources, quote validation), `test_bundles.py` (matching
incl. colloquial/English phrasing, Maria→Anna with/without letter, Stefan Gesundheit + Familiengeschichte, scopes).
