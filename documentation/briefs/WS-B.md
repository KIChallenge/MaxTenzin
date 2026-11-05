# WS-B — Benefits catalog + eligibility, directory, legal search, medications

> **Historical brief** — the task as handed to the workstream at the start. Current behaviour: the service READMEs, `documentation/architecture.md` and `documentation/services.md`.

**Branch:** `ws/B-benefits` · **Owned paths:** `services/api/app/services/{benefits,directory,legal,medications,values}/`, `knowledge/benefits.yaml`, `knowledge/offices.yaml`, `knowledge/schema/benefits.schema.json`
Read `CLAUDE.md` first (invariants!). Contracts: `app/contracts/benefits.py`, `misc.py`, `common.py` — do not change them (use Contract requests in PROGRESS.md).

## Goal
Replace the stubs with real deterministic services. The benefit catalog is the heart of the "infrastructure first" thesis: every criterion, amount and next step is source-cited.

## Inputs (committed, no docs/ needed)
- `knowledge/extracted/legal/paragraphs.jsonl` (1976 ¶, 19 laws: BPGG, ASVG, RPGG_2012, RRZ_2008, RRK_2021, RBZRehab_2005, RVU, FLAG, KBGG, MuKiPassV_2002, KrankenO_OEGK_2025, Satzung_OEGK_2025, RUF_2020 …)
- `knowledge/extracted/values/veraendw.json` (2026: Pflegegeld Stufen, Rezeptgebühr 7,55 €, Befreiungsgrenzen 1.308,39/2.064,12 €, +201,88/Kind, Reha-Zuzahlung, AZ-Richtsatz, KBG 41,14 €/Tag)
- `knowledge/extracted/serviceratgeber/pages.jsonl` (printed pages; cite as "ÖGK Serviceratgeber 2026, S. N"). Key pages: 23–25 Vorsorge, 32 Impfungen, 42–44 Rezeptgebühr, 45–46 Heilbehelfe/Hilfsmittel, 47–49 Krankenhaus/Hauskrankenpflege/Reha, 62 Kur, 63–64 Transportkosten, 66–75 Kind, 85 Unterstützungsfonds, 89–115 Kundenservice addresses
- `knowledge/forms/templates/*.fields.json` (Fahrtkosten form p.2 has the Fahrtkosten rules: >20 km, 7,20 €/10,80 €, 0,13/0,22 €/km, Strahlen-/Chemotherapie exception)

## Tasks
- [ ] `knowledge/benefits.yaml` + JSON schema: ~14 benefits across areas A–F. Minimum: `pflegegeld`, `reha_onko`, `fsw_mobile_pflege`, `pflegeberatung` (kostenlos, PAL080 §9), `krankentransport`, `fahrtkostenzuschuss`, `rezeptgebuehrenbefreiung`, `rezeptgebuehrenobergrenze`, `hauskrankenpflege`, `unterstuetzungsfonds`, `vorsorgeuntersuchung`, `familienbeihilfe`, `kinderbetreuungsgeld`, `eltern_kind_pass`. Each: name_de, plain_de (Einfache Sprache), area, provider, form_ids, required_documents_de, legal_basis (law_key+nr → resolve to SourceRef with in-force date from paragraphs.jsonl), sources (page refs), value_refs.
- [ ] Eligibility engine `benefits/service.py`: pure functions per benefit over `facts` + person profile + document recommendations (from `/api/documents/{id}/analysis` contract — accept them as input list, don't call LLM). Output `EligibilityResult` with criteria (met True/False/None + explanation + source), `missing_fields` (what the agent should ask), `next_steps_de`, `amounts` from values, `rule_ids` like `pflegegeld.v1`. Status semantics: likely / possible / needs_info / not_applicable. Never claim a definitive entitlement: the Träger decides ("voraussichtlich", "kommt in Frage").
- [ ] Golden test: Anna (78, Wien 1030, alone, ÖGK, discharge letter with r1–r5 as in `app/fixtures.py`) → pflegegeld needs_info, reha_onko possible, fsw_mobile_pflege likely/possible, krankentransport needs_info (Gehunfähigkeit ärztlich bestätigt?), fahrtkostenzuschuss: Strahlentherapie exception explained but ≤20 km in Wien → not_applicable or needs_info with explanation, rezeptgebuehrenbefreiung needs_info(net_income_monthly). Stefan (39) → vorsorgeuntersuchung likely. Stefan for Lena (2y) → familienbeihilfe/kinderbetreuungsgeld/eltern_kind_pass possible.
- [ ] Rezeptgebühr calculator: given net income + household → befreit / Obergrenze 2 % / nicht befreit, using values only.
- [ ] `knowledge/offices.yaml` from Serviceratgeber S. 89–115 (Wien first: ÖGK Kundenservicestellen with PLZ), PVA Landesstellen (PAL080 p.8 in `pva_pflegegeld_pal080.fields.json` page_text), FSW (Guglgasse 7–9, 1030 Wien, 01 24 5 24), 1450. Directory endpoint filters by topic + nearest by PLZ district.
- [ ] Legal search: build SQLite FTS5 index from paragraphs.jsonl at first use (file under `var/`, gitignored), BM25 ranking, boost allowlisted core laws; keep endpoint signatures.
- [ ] Medications: keep administrative wording; add `GET /api/medications/{pharma_nr}`.
- [ ] Tests in each `tests/` folder; per-service README.md.

## Definition of Done
`make test-api` + `make lint` green; golden tests pass; every EligibilityResult criterion has a source; PROGRESS.md row updated; commits on `ws/B-benefits`.
