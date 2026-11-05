"""Phase-0 smoke tests: every endpoint answers with a contract-valid payload; auth, scopes and audit work."""

from app.conftest import auth

MARIA_FOR_ANNA = auth("maria", "anna")


def test_routes_mounted(client):
    paths = set(client.app.openapi()["paths"])
    for p in ["/api/identity/login", "/api/documents", "/api/benefits/eligibility", "/api/prevention/overview",
              "/api/forms/sessions/{session_id}/next-questions", "/api/cases", "/api/notifications", "/api/directory/offices",
              "/api/medications/search", "/api/legal/search", "/api/values/{key}", "/api/audit", "/api/agent/chat"]:
        assert p in paths, p


def test_login_and_me(client):
    s = client.post("/api/identity/login", json={"persona_id": "maria"}).json()
    assert s["token"] == "demo-maria" and s["delegations"][0]["grantor_id"] == "anna"
    me = client.get("/api/identity/me", headers=MARIA_FOR_ANNA).json()
    assert me["subject"]["id"] == "anna" and "prepare_applications" in me["scopes"]


def test_unauthenticated_and_no_delegation(client):
    assert client.get("/api/benefits").status_code == 401
    assert client.get("/api/benefits", headers=auth("stefan", "anna")).status_code == 403


def test_scope_denied_is_audited(client):
    # Anna did NOT grant Maria view_health_prevention
    r = client.get("/api/prevention/overview", headers=auth("maria", "anna", via="agent", tool="get_prevention"))
    assert r.status_code == 403
    events = client.get("/api/audit", headers=auth("anna")).json()
    denied = [e for e in events if e["path"] == "/api/prevention/overview"]
    assert denied and denied[0]["allowed"] is False and denied[0]["via"] == "agent" and denied[0]["tool"] == "get_prevention"


def test_revoked_scope_blocks_agent(client):
    assert client.post("/api/forms/definitions/pva_pflegegeld_pal080/sessions", headers=MARIA_FOR_ANNA).status_code == 200
    client.put("/api/identity/delegations/del-anna-maria/scopes", headers=auth("anna"), json=["read_documents"])
    assert client.post("/api/forms/definitions/pva_pflegegeld_pal080/sessions", headers=MARIA_FOR_ANNA).status_code == 403


def test_values_and_legal_real(client):
    v = client.get("/api/values/pflegegeld_stufe_3", headers=auth("anna")).json()
    assert v["value"] == 592.6 and "BPGG" in v["legal_ref"]
    p = client.get("/api/legal/paragraphs/BPGG/4", headers=auth("anna")).json()
    assert "sechs Monate" in p["text"] and p["citation_de"].startswith("§ 4 BPGG")
    hits = client.get("/api/legal/search", params={"q": "Pflegegeld Stufe", "law": "BPGG"}, headers=auth("anna")).json()
    assert hits and hits[0]["paragraph"]["law_key"] == "BPGG"


def test_medications_real(client):
    meds = client.get("/api/medications/search", params={"q": "Amlodipin"}, headers=auth("anna")).json()
    assert meds and meds[0]["box"] in ("G", "Y") and "Rezeptgebühr" in meds[0]["patient_cost_note_de"]


def test_stubs_answer(client):
    h = MARIA_FOR_ANNA
    assert client.post("/api/documents/doc-anna-entlassung/analyze", headers=h).json()["recommendations"]
    assert client.post("/api/benefits/eligibility", headers=h, json={"subject_id": "anna"}).json()[0]["benefit"]["id"] == "pflegegeld"
    sess = client.post("/api/forms/definitions/pva_pflegegeld_pal080/sessions", headers=h).json()
    nq = client.get(f"/api/forms/sessions/{sess['id']}/next-questions", headers=h).json()
    assert any(q["id"] == "Leiden" for q in nq["questions"])
    client.patch(f"/api/forms/sessions/{sess['id']}", headers=h, json={"values": {"Leiden": "laut Entlassungsbrief"}})
    assert not client.get(f"/api/forms/sessions/{sess['id']}/next-questions", headers=h).json()["questions"]
    assert client.post(f"/api/forms/sessions/{sess['id']}/render", headers=h).headers["content-type"] == "application/pdf"
    case = client.post("/api/cases", headers=h, json={"subject_id": "anna", "title_de": "Fall", "document_id": "doc-anna-entlassung"})
    assert case.json()["steps"] and client.get("/api/cases", headers=h).json()
    assert client.get("/api/prevention/overview", headers=auth("stefan")).json()["items"]
    assert client.get("/api/notifications", headers=auth("stefan")).json()
    assert client.get("/api/directory/offices", params={"topic": "pflegegeld"}, headers=h).json()
    assert client.post("/api/agent/chat", headers=h, json={"message": "Hallo"}).json()["reply"]
