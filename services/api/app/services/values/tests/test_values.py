from app.services.values import service
from app.tests.conftest import auth

EXPECTED_2026 = {"rezeptgebuehr": 7.55, "rgb_befreiungsgrenze_alleinstehend": 1308.39, "rgb_befreiungsgrenze_paar": 2064.12,
                 "rgb_erhoehung_pro_kind": 201.88, "pflegegeld_stufe_1": 206.2, "pflegegeld_stufe_7": 2214.8,
                 "kbg_taeglich": 41.14, "reha_stufe1_pro_tag": 11.06}


def test_2026_values():
    for k, v in EXPECTED_2026.items():
        val = service.require_value(k)
        assert val.value == v and val.year == 2026 and "veraendW" in val.source.label, k


def test_endpoints(client):
    h = auth("stefan")
    assert client.get("/api/values/rezeptgebuehr", headers=h).json()["source"]["ref"] == "veraendW#20/2026/rezeptgebuehr"
    assert client.get("/api/values/nope", headers=h).status_code == 404
    assert len(client.get("/api/values", headers=h).json()) == len(service.list_values())
