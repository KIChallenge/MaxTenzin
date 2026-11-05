from app.conftest import auth


def test_laws_list(client):
    laws = client.get("/api/legal/laws", headers=auth("anna")).json()
    keys = {x["key"] for x in laws}
    assert {"BPGG", "ASVG", "FLAG"} <= keys and all(x["paragraphs"] > 0 for x in laws)


def test_form_template_served(client):
    r = client.get("/api/forms/definitions/pva_pflegegeld_pal080/template", headers=auth("anna"))
    assert r.status_code == 200 and r.content[:4] == b"%PDF"


def test_law_paragraphs_toc(client):
    r = client.get("/api/legal/laws/BPGG/paragraphs", headers=auth("anna"))
    assert r.status_code == 200
    toc = r.json()
    paras = [e["nr"] for e in toc if e["type"] == "PARA"]
    assert paras.index("2") < paras.index("3") < paras.index("4") < paras.index("10")   # natural, not lexical
    p4 = next(e for e in toc if e["type"] == "PARA" and e["nr"] == "4")
    assert p4["label"] == "§ 4" and " – " not in p4["heading"] and p4["in_force"]
    assert toc[-1]["type"] != "PARA" or all(e["type"] == "PARA" for e in toc)   # annexes after paragraphs
    assert client.get("/api/legal/laws/NOPE/paragraphs", headers=auth("anna")).status_code == 404
    assert client.get("/api/legal/laws/BPGG/paragraphs").status_code == 401
