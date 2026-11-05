"""Golden eligibility scenarios (demo personas). Deterministic: as_of fixed to the demo date."""

import pytest

from app.tests.conftest import auth

AS_OF = "2026-11-05"
MARIA_FOR_ANNA = auth("maria", "anna")


def _run(client, headers, subject, facts=None, docs=None, ids=None):
    body = {"subject_id": subject, "facts": {"as_of": AS_OF, **(facts or {})}, "document_ids": docs or []}
    if ids is not None:
        body["benefit_ids"] = ids
    r = client.post("/api/benefits/eligibility", headers=headers, json=body)
    assert r.status_code == 200, r.text
    return {e["benefit"]["id"]: e for e in r.json()}


def _assert_sourced(results):
    for e in results.values():
        assert e["rule_ids"] == [f"{e['benefit']['id']}.v1"]
        assert e["next_steps_de"][-1].startswith("Unverbindliche Information")
        for c in e["criteria"]:
            assert c["source"] and c["source"]["label"], (e["benefit"]["id"], c["id"])
        for a in e["amounts"]:
            assert a["source"]["label"] and a["unit"], (e["benefit"]["id"], a)


@pytest.fixture
def anna(client):
    return _run(client, MARIA_FOR_ANNA, "anna", docs=["doc-anna-entlassung"])


def test_anna_statuses(anna):
    st = {k: v["status"] for k, v in anna.items()}
    assert st["pflegegeld"] == "needs_info"
    assert st["reha_onko"] == "possible"
    assert st["fsw_mobile_pflege"] in ("likely", "possible")
    assert st["krankentransport"] == "needs_info"
    assert st["fahrtkostenzuschuss"] in ("needs_info", "not_applicable")
    assert st["rezeptgebuehrenbefreiung"] == "needs_info"
    assert st["familienbeihilfe"] == st["kinderbetreuungsgeld"] == st["eltern_kind_pass"] == "not_applicable"
    _assert_sourced(anna)


def test_anna_details(anna):
    pg = anna["pflegegeld"]
    assert {"care_hours_estimate", "care_need_months"} <= set(pg["missing_fields"])
    doc = next(c for c in pg["criteria"] if c["id"] == "doc_r2")
    assert doc["source"]["kind"] == "document" and doc["source"]["quote"].startswith("Aufgrund")
    assert [a["value"] for a in pg["amounts"]][:3] == [206.2, 380.3, 592.6]          # veraendW 2026
    assert "walking_unable_confirmed" in anna["krankentransport"]["missing_fields"]
    assert "Wiens" in next(c for c in anna["fahrtkostenzuschuss"]["criteria"] if c["id"] == "fk_distance")["explanation_de"]
    rgb = anna["rezeptgebuehrenbefreiung"]
    assert rgb["missing_fields"] == ["net_income_monthly"]   # household derived from "Lebt allein …" in the letter
    assert any(c["source"]["kind"] == "document" for c in anna["reha_onko"]["criteria"])


def test_anna_with_radiotherapy_in_vienna(client):
    res = _run(client, MARIA_FOR_ANNA, "anna", docs=["doc-anna-entlassung"],
               facts={"treatment_type": "strahlentherapie", "treatment_outside_home_town": False,
                      "walking_unable_confirmed": True},
               ids=["fahrtkostenzuschuss", "krankentransport"])
    fk = res["fahrtkostenzuschuss"]
    assert fk["status"] == "not_applicable"
    crit = {c["id"]: c for c in fk["criteria"]}
    assert crit["fk_entitled_group"]["met"] is True and "Strahlentherapie" in crit["fk_entitled_group"]["explanation_de"]
    assert crit["fk_distance"]["met"] is False
    kt = res["krankentransport"]
    assert kt["status"] == "likely"
    assert kt["amounts"][0]["value"] == 0.0 and "47 Abs. 3b" in kt["amounts"][0]["source"]["label"]


def test_anna_low_income_rgb_and_pflegegeld_level(client):
    res = _run(client, MARIA_FOR_ANNA, "anna", docs=["doc-anna-entlassung"],
               facts={"net_income_monthly": 1200, "care_need_months": 12, "care_hours_estimate": 100},
               ids=["pflegegeld", "rezeptgebuehrenbefreiung", "rezeptgebuehrenobergrenze"])
    assert res["rezeptgebuehrenbefreiung"]["status"] == "likely"
    pg = res["pflegegeld"]
    assert pg["status"] == "likely"
    est = [a for a in pg["amounts"] if a["estimated"]]
    assert len(est) == 1 and est[0]["key"] == "pflegegeld_stufe_2"
    rego = res["rezeptgebuehrenobergrenze"]["amounts"][0]
    assert rego["value"] == 314.01      # 2 % × 12 × 1.308,39 (Mindestgrenze, RRZ § 16 Abs. 4)


def test_stefan_vorsorge(client):
    res = _run(client, auth("stefan"), "stefan")
    assert res["vorsorgeuntersuchung"]["status"] == "likely"
    assert res["vorsorgeuntersuchung"]["amounts"][0]["value"] == 0.0
    # Stefan has Obsorge for Lena -> family benefits are evaluated for her
    assert res["familienbeihilfe"]["status"] == "possible"
    _assert_sourced(res)


def test_stefan_for_lena(client):
    res = _run(client, auth("stefan", "lena"), "lena")
    for b in ("familienbeihilfe", "kinderbetreuungsgeld", "eltern_kind_pass"):
        assert res[b]["status"] == "possible", b
    assert res["vorsorgeuntersuchung"]["status"] == "not_applicable"
    ekp = res["eltern_kind_pass"]["criteria"][0]["explanation_de"]
    assert "6. Untersuchung" in ekp and "jetzt" in ekp
    assert res["kinderbetreuungsgeld"]["amounts"][0]["value"] == 41.14
    _assert_sourced(res)


def test_subject_mismatch_and_scope(client):
    r = client.post("/api/benefits/eligibility", headers=MARIA_FOR_ANNA, json={"subject_id": "maria"})
    assert r.status_code == 403
    # documents require read_documents: revoke and retry
    client.put("/api/identity/delegations/del-anna-maria/scopes", headers=auth("anna"), json=["prepare_applications"])
    r = client.post("/api/benefits/eligibility", headers=MARIA_FOR_ANNA,
                    json={"subject_id": "anna", "document_ids": ["doc-anna-entlassung"]})
    assert r.status_code == 403
    assert client.post("/api/benefits/eligibility", headers=MARIA_FOR_ANNA, json={"subject_id": "anna"}).status_code == 200


def test_unknown_document_and_benefit(client):
    r = client.post("/api/benefits/eligibility", headers=auth("stefan"),
                    json={"subject_id": "stefan", "document_ids": ["doc-anna-entlassung"]})
    assert r.status_code == 404
    r = client.post("/api/benefits/eligibility", headers=auth("stefan"), json={"subject_id": "stefan", "benefit_ids": ["x"]})
    assert r.status_code == 404


def test_recommendations_as_facts(client):
    rec = {"id": "x1", "text_de": "Im Dokument wird Reha empfohlen.", "quote": "Reha empfohlen.", "page": 2,
           "category": "rehabilitation", "related_benefit_ids": ["reha_onko"]}
    res = _run(client, auth("stefan"), "stefan", facts={"recommendations": [rec], "document_filename": "Brief.pdf"},
               ids=["reha_onko"])
    assert res["reha_onko"]["status"] == "possible"
    assert res["reha_onko"]["criteria"][0]["source"]["label"] == "Brief.pdf, S. 2"


def test_audit_records_rules(client):
    _run(client, MARIA_FOR_ANNA, "anna", ids=["pflegegeld"])
    events = client.get("/api/audit", headers=auth("anna")).json()
    ev = [e for e in events if e["path"] == "/api/benefits/eligibility"][-1]
    assert "pflegegeld.v1" in ev["rule_ids"] and any("BPGG" in s for s in ev["sources"])
