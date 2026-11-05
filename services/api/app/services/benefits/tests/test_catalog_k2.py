"""WS-K2 catalog additions: aids, carer benefits, Sozialhilfe Wien (external), offers (Serviceratgeber "Gesund leben")."""

import pytest

from app.contracts.common import SourceKind
from app.services.benefits import catalog
from app.services.benefits.catalog import SourceSpec
from app.tests.conftest import auth

AS_OF = "2026-11-05"
MARIA_FOR_ANNA = auth("maria", "anna")
NEW_BENEFITS = {"heilbehelfe_hilfsmittel", "ersatzpflege", "foerderung_24h_betreuung", "pflegekarenzgeld",
                "selbstversicherung_pflege", "sozialhilfe_wien"}


def _run(client, headers, subject, facts=None, ids=None, docs=None):
    body = {"subject_id": subject, "facts": {"as_of": AS_OF, **(facts or {})}, "document_ids": docs or []}
    if ids is not None:
        body["benefit_ids"] = ids
    r = client.post("/api/benefits/eligibility", headers=headers, json=body)
    assert r.status_code == 200, r.text
    return {e["benefit"]["id"]: e for e in r.json()}


def test_new_entries_present_and_offers_marked():
    ids = set(catalog.entries())
    assert NEW_BENEFITS <= ids
    offers = {b.id for b in catalog.benefits("offer")}
    assert {"angebot_bewegt_im_park", "angebot_gesunder_ruecken", "angebot_richtig_essen",
            "angebot_gesund_leben_regional"} <= offers
    assert all(o.startswith("angebot_") for o in offers)
    assert not offers & {b.id for b in catalog.benefits("benefit")}


def test_external_sources_have_url_and_retrieval_date():
    bip = catalog.get("angebot_bewegt_im_park").benefit.sources[0]
    assert bip.kind == SourceKind.external and bip.ref.startswith("https://") and bip.retrieved == "2026-11-05"
    assert "abgerufen am 05.11.2026" in bip.label
    sh = catalog.get("sozialhilfe_wien")
    assert sh.benefit.sources[0].kind == SourceKind.external
    assert all(src.kind == SourceKind.external for _, src in sh.criteria.values())


def test_brochure_quotes_are_validated_at_load_time():
    with pytest.raises(KeyError):
        catalog.resolve(SourceSpec(page=45, quote="Die ÖGK zahlt alles."))
    with pytest.raises(ValueError):
        SourceSpec(url="http://example.org", label="x", retrieved="2026-11-05")      # https only
    with pytest.raises(ValueError):
        SourceSpec(url="https://example.org", label="x")                             # needs retrieved
    ref = catalog.resolve(SourceSpec(page=45, quote="mindestens jedoch 46,20 Euro."))
    assert ref.quote and ref.label.endswith("S. 45")


def test_catalog_kind_filter(client):
    h = auth("stefan")
    offers = client.get("/api/benefits", params={"kind": "offer"}, headers=h).json()
    assert offers and all(b["id"].startswith("angebot_") for b in offers)
    benefits = client.get("/api/benefits", params={"kind": "benefit"}, headers=h).json()
    assert benefits[0]["id"] == "pflegegeld" and not any(b["id"].startswith("angebot_") for b in benefits)


def test_default_run_excludes_offers(client):
    res = _run(client, auth("stefan"), "stefan")
    assert not any(k.startswith("angebot_") for k in res)
    assert NEW_BENEFITS <= set(res)


def test_anna_heilbehelfe_via_explicit_fact(client):
    base = _run(client, MARIA_FOR_ANNA, "anna", ids=["heilbehelfe_hilfsmittel"])["heilbehelfe_hilfsmittel"]
    assert base["status"] == "needs_info" and "aid_needed" in base["missing_fields"]
    # Rollator documented in the discharge letter (p.3) -> the agent passes it as an explicit fact
    hh = _run(client, MARIA_FOR_ANNA, "anna", facts={"aid_needed": True, "aid_type": "Rollator"},
              ids=["heilbehelfe_hilfsmittel"])["heilbehelfe_hilfsmittel"]
    assert hh["status"] == "possible" and hh["missing_fields"] == ["aid_prescribed"]
    copay = hh["amounts"][0]
    assert copay["value"] == 46.2 and copay["source"]["label"].endswith("S. 45") and "46,20" in copay["source"]["quote"]
    assert any("Rollator" in s for s in hh["next_steps_de"])
    ok = _run(client, MARIA_FOR_ANNA, "anna", facts={"aid_needed": True, "aid_prescribed": True, "rgb_exempt": True},
              ids=["heilbehelfe_hilfsmittel"])["heilbehelfe_hilfsmittel"]
    assert ok["status"] == "likely" and ok["amounts"][0]["value"] == 0.0


def test_carer_benefits(client):
    ids = ["ersatzpflege", "foerderung_24h_betreuung", "pflegekarenzgeld", "selbstversicherung_pflege"]
    res = _run(client, MARIA_FOR_ANNA, "anna", ids=ids)
    assert {k: v["status"] for k, v in res.items()} == {k: "needs_info" for k in ids}
    assert "pflegegeld_level" in res["ersatzpflege"]["missing_fields"]
    res = _run(client, MARIA_FOR_ANNA, "anna", ids=ids,
               facts={"pflegegeld_level": 3, "main_carer_since_months": 14, "carer_prevented": True,
                      "care_24h_needed": True, "pflegekarenz_agreed": True, "caregiver_insured_3m": True,
                      "caregiver_main_carer": True})
    assert res["ersatzpflege"]["status"] == "possible"            # no legal entitlement -> capped
    assert res["foerderung_24h_betreuung"]["status"] == "possible"
    assert res["pflegekarenzgeld"]["status"] == "likely"
    assert res["selbstversicherung_pflege"]["status"] == "likely"
    res = _run(client, MARIA_FOR_ANNA, "anna", ids=ids, facts={"pflegegeld_level": 2})
    assert res["ersatzpflege"]["status"] == res["selbstversicherung_pflege"]["status"] == "not_applicable"
    assert res["foerderung_24h_betreuung"]["status"] == "not_applicable"
    # demenziell erkrankt (explicit fact) -> Stufe 1 suffices for Ersatzpflege
    res = _run(client, MARIA_FOR_ANNA, "anna", ids=["ersatzpflege"],
               facts={"pflegegeld_level": 1, "dementia_documented": True, "main_carer_since_months": 12})
    assert res["ersatzpflege"]["status"] == "possible"
    for r in res.values():
        assert r["next_steps_de"][-1] == "Unverbindliche Information – die Entscheidung trifft das Sozialministeriumservice."


def test_sozialhilfe_wien(client):
    sh = _run(client, MARIA_FOR_ANNA, "anna", ids=["sozialhilfe_wien"])["sozialhilfe_wien"]
    assert sh["status"] == "needs_info" and sh["missing_fields"] == ["financial_hardship"] and sh["amounts"] == []
    sh = _run(client, MARIA_FOR_ANNA, "anna", ids=["sozialhilfe_wien"],
              facts={"financial_hardship": True})["sozialhilfe_wien"]
    assert sh["status"] == "possible"


def test_offers(client):
    ids = ["angebot_bewegt_im_park", "angebot_gesunder_ruecken", "angebot_trittsicher", "angebot_richtig_essen",
           "angebot_bgf", "angebot_therapie_aktiv"]
    st = _run(client, auth("stefan"), "stefan", ids=ids)
    assert st["angebot_bewegt_im_park"]["status"] == "likely"
    season = next(c for c in st["angebot_bewegt_im_park"]["criteria"] if c["id"] == "of_season")
    assert "Juni bis September" in season["explanation_de"]                  # November: next season
    assert st["angebot_gesunder_ruecken"]["status"] == "likely"
    assert st["angebot_trittsicher"]["status"] == "not_applicable"           # Stefan is 39
    assert st["angebot_richtig_essen"]["status"] == "likely"                 # Lena (2) in Obsorge
    assert st["angebot_bgf"]["status"] == "possible"                         # for Betriebe
    assert st["angebot_therapie_aktiv"]["status"] == "needs_info"
    assert st["angebot_therapie_aktiv"]["missing_fields"] == ["diabetes_type2"]
    anna = _run(client, MARIA_FOR_ANNA, "anna", ids=["angebot_trittsicher", "angebot_richtig_essen"])
    assert anna["angebot_trittsicher"]["status"] == "likely"
    assert anna["angebot_richtig_essen"]["status"] == "needs_info"
    for r in [*st.values(), *anna.values()]:
        assert r["next_steps_de"][-1].startswith("Unverbindliche Information")
        assert all(c["source"]["label"] for c in r["criteria"])
