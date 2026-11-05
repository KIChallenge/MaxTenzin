from app.conftest import auth

H = auth("maria", "anna")


def test_case_from_discharge_letter(client):
    case = client.post("/api/cases", headers=H, json={"subject_id": "anna", "title_de": "Nach dem Spital",
                                                      "document_id": "doc-anna-entlassung", "benefit_ids": ["pflegeberatung"]}).json()
    titles = [s["title_de"] for s in case["steps"]]
    assert "Pflegegeldanspruch prüfen" in titles and titles[-1].startswith("Kostenlose Pflegeberatung")
    pg = next(s for s in case["steps"] if s["benefit_id"] == "pflegegeld")
    assert pg["source"]["kind"] == "document"
    upd = client.patch(f"/api/cases/{case['id']}/steps/{pg['id']}", headers=H, json={"form_session_id": "fs-1"}).json()
    step = next(s for s in upd["steps"] if s["id"] == pg["id"])
    assert step["status"] == "in_progress" and step["form_session_id"] == "fs-1"
    assert client.get("/api/cases", headers=H).json()[-1]["id"] == case["id"]


def test_case_isolation(client):
    case = client.post("/api/cases", headers=H, json={"subject_id": "anna", "title_de": "x"}).json()
    assert client.get(f"/api/cases/{case['id']}", headers=auth("stefan")).status_code == 404
