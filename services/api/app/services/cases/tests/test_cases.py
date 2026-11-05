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


def test_case_created_after_lebenslage_gets_its_steps(client):
    """Demo order: confirm the Lebenslage first, then 'Als Mein Fall anlegen' – the Meldepflicht step must be there."""
    from datetime import date, timedelta

    end = (date.today() - timedelta(days=7)).isoformat()
    r = client.post("/api/situation/episodes", headers=H,
                    json={"type": "hospital", "start": (date.today() - timedelta(days=20)).isoformat(), "end": end})
    assert r.status_code == 200
    case = client.post("/api/cases", headers=H, json={"subject_id": "anna", "title_de": "Nach dem Spital",
                                                      "document_id": "doc-anna-entlassung",
                                                      "benefit_ids": ["hauskrankenpflege"]}).json()
    from app.core.db import store

    client.delete(f"/api/situation/episodes/{r.json()['id']}", headers=H)   # shared test DB: leave no state behind
    store.delete("cases", case["id"])
    titles = [s["title_de"] for s in case["steps"]]
    assert any("an die PVA melden" in t for t in titles), titles
    assert not any("hauskrankenpflege" in t for t in titles)   # German name, never the internal id
