# benefits

## Purpose
Benefit catalog + deterministic eligibility ("kommt voraussichtlich in Frage"). No LLM. Every criterion carries a
`SourceRef`; every amount comes from veraendW (values service) or, where the rule defines the amount itself, from the
cited paragraph (Satzung ÖGK § 46 Abs. 5 Fahrtkosten, RRZ § 13 Abs. 1a Obergrenze).

## Endpoints
| Method | Path | Notes |
|---|---|---|
| GET | `/api/benefits?area=A..F` | catalog (order of `knowledge/benefits.yaml`, `pflegegeld` first) |
| GET | `/api/benefits/{id}` | one benefit incl. `legal_basis` (with in-force date) and `sources` |
| POST | `/api/benefits/eligibility` | `EligibilityRequest` → `list[EligibilityResult]` (catalog order) |
| GET | `/api/benefits/rezeptgebuehr/check?net_income_monthly=&household=alleinstehend\|paar&children_count=&chronic_illness_expenses=&receives_ausgleichszulage=` | calculator → results for `rezeptgebuehrenbefreiung` + `rezeptgebuehrenobergrenze` |

`subject_id` must equal the acting context (`X-Subject-Id`), else 403. `document_ids` need scope `read_documents`;
analyses are read from store collection `document_analyses` (WS-D), fallback: golden `doc-anna-entlassung` for Anna.

### Facts the engine understands (`facts`, all optional — missing ones appear in `missing_fields`)
| key | type | used by |
|---|---|---|
| `care_need_months`, `care_hours_estimate` | number | pflegegeld (Stufe estimate from BPGG § 4 Abs. 2) |
| `receives_pflegegeld`, `pflegegeld_applied` | bool | pflegeberatung |
| `care_need_at_home` | bool | fsw_mobile_pflege |
| `home_nursing_ordered` | bool | hauskrankenpflege |
| `reha_application_with_medical_statement`, `gross_income_monthly` | bool, number | reha_onko (Zuzahlung tier) |
| `walking_unable_confirmed` | bool | krankentransport |
| `treatment_type` | `strahlentherapie\|chemotherapie\|immuntherapie\|dialyse\|…` | krankentransport, fahrtkostenzuschuss |
| `distance_km`, `treatment_outside_home_town`, `companion_needed` | number, bool, bool | fahrtkostenzuschuss |
| `rgb_exempt` | bool (already befreit) | fahrtkostenzuschuss, krankentransport |
| `net_income_monthly`, `household` (`alleinstehend\|paar`), `lives_alone`, `children_count`, `chronic_illness_expenses`, `receives_ausgleichszulage` | | rezeptgebuehren* |
| `costs_eur` | number | unterstuetzungsfonds |
| `familienbeihilfe_received`, `shared_household_with_child` | bool | familienbeihilfe, kinderbetreuungsgeld |
| `recommendations` (+ `document_filename`) | list of `Recommendation` | alternative to `document_ids` |
| `as_of` | ISO date | age computations (tests/demo) |

Household is also derived from the document (`ExtractedPerson.living_situation` containing "allein").
Family benefits: if the subject is a minor they are evaluated for the subject; for adults, for the youngest child
in their Obsorge (delegations with relation "Obsorge").

## Rules & knowledge
- `knowledge/benefits.yaml` (schema `knowledge/schema/benefits.schema.json`, generated from `catalog.py`): 14 benefits,
  areas A Vorsorge · B Gesund werden · C Reha · D Pflege · E Kosten · F Familie.
- `service.py`: one pure evaluator per benefit, `rule_ids = ["<benefit>.v1"]`.
- Status: any criterion `False` → `not_applicable`; all `True` → `likely`; else `needs_info`. Discretionary benefits
  without legal entitlement (reha_onko, unterstuetzungsfonds, family benefits) are capped at `possible`.
- Every result ends with "Unverbindliche Information – die Entscheidung trifft …".

## Sources
SozDok paragraphs (BPGG, ASVG, RRZ 2008, Satzung ÖGK 2025, RUF 2020, RVU, FLAG, KBGG, MuKiPassV 2002, RRK 2021),
veraendW 2026, ÖGK Serviceratgeber 2026 (S. 23–24, 43–44, 48–49, 63–64, 69–75, 85), form templates (PAL 080, FSW
Förderantrag, ÖGK Fahrtkosten, Kur/Reha).

## Limitations
- Familienbeihilfe amounts are not in veraendW → no amount shown. FSW has no law in the corpus → form sources only.
- The engine does not parse document quotes: medical facts (e.g. `treatment_type`) must be passed as facts.
- Pflegegeld Stufe 5–7 depend on qualitative criteria; the estimate stops at Stufe 4.

## Tests
`app/services/benefits/tests/`: catalog integrity + schema sync, Anna/Stefan/Lena goldens, Rezeptgebühr calculator.
