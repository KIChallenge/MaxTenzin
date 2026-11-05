from app.core.knowledge import yaml_file
from app.services.benefits import catalog
from app.services.directory import service
from app.tests.conftest import auth

GENERIC = {"oegk_kundenservice", "gesundheitszentrum", "pflege", "mobile_pflege", "reha", "pension", "rezeptgebuehr",
           "familie", "gesundheitsberatung", "akut"}


def test_all_offices_sourced_and_topics_known():
    offs = service.offices()
    assert len(offs) == len(yaml_file("offices.yaml")["offices"]) >= 25
    known = set(catalog.entries()) | GENERIC
    for o in offs:
        assert o.source.label and o.topics, o.id
        assert set(o.topics) <= known, (o.id, set(o.topics) - known)
    assert len({o.id for o in offs}) == len(offs)


def test_every_benefit_has_an_office():
    no_office_in_sources = {"Finanzamt Österreich", "Sozialministeriumservice", "Stadt Wien – MA 40"}
    for bid, e in catalog.entries().items():
        if e.benefit.provider in no_office_in_sources:  # addresses not in our sources (benefit text names the contact)
            continue
        if e.spec.kind == "offer":                       # programmes: contact/URL is part of the offer's next steps
            continue
        assert service.search(topic=bid), bid


def test_pflegegeld_anna_nearest_is_vienna(client):
    r = client.get("/api/directory/offices", params={"topic": "pflegegeld", "zip": "1030"},
                   headers=auth("maria", "anna")).json()
    assert r[0]["id"] in ("pva-wien-kundenzone", "pva-wien") and r[0]["city"] == "Wien"
    assert r[0]["source"]["label"].startswith("PAL 080, S. 8")


def test_oegk_nearest_for_stefan():
    res = service.search(topic="rezeptgebuehrenbefreiung", zip_="1120")
    assert res[0].id == "oegk-ks-meidling"
    assert res[0].source.label == "ÖGK Serviceratgeber 2026, S. 95"


def test_fsw_and_1450():
    fsw = service.search(topic="fsw_mobile_pflege")
    assert fsw[0].address == "Guglgasse 7–9" and fsw[0].zip == "1030" and fsw[0].phone == "01 24 5 24"
    assert service.search(topic="gesundheitsberatung")[0].phone == "1450"


def test_outside_vienna_ranking():
    res = service.search(topic="pflegegeld", zip_="8010")
    assert res[0].id == "pva-steiermark"
    assert service.search(topic="pflegegeld", zip_="8010", limit=2)[1].provider == "PVA"
