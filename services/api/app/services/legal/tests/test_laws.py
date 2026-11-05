from app.conftest import auth


def test_laws_list(client):
    laws = client.get("/api/legal/laws", headers=auth("anna")).json()
    keys = {x["key"] for x in laws}
    assert {"BPGG", "ASVG", "FLAG"} <= keys and all(x["paragraphs"] > 0 for x in laws)


def test_form_template_served(client):
    r = client.get("/api/forms/definitions/pva_pflegegeld_pal080/template", headers=auth("anna"))
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
