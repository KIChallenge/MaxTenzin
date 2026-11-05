"""Integration: suggestions -> consent -> inbox reminder + case steps via the cases API (no direct store writes)."""

from app.conftest import auth

H = auth("maria", "anna")


def test_situation_reminders_and_steps_flow(client):
    client.post("/api/forms/definitions/pva_pflegegeld_pal080/sessions", headers=H)  # Pflegegeld involved
    case = client.post("/api/cases", headers=H, json={"subject_id": "anna", "title_de": "Nach dem Spital",
                                                      "document_id": "doc-anna-entlassung"}).json()
    sugg = client.post("/api/situation/suggestions/from-document/doc-anna-entlassung", headers=H).json()
    assert sugg and all(e["status"] == "suggested" for e in sugg)
    assert not [n for n in client.get("/api/notifications", headers=H).json() if n["kind"] == "situation"]
    hosp = next(e for e in sugg if e["type"] == "hospital")
    assert client.post(f"/api/situation/suggestions/{hosp['id']}/confirm", headers=H).status_code == 200
    inbox = [n for n in client.get("/api/notifications", headers=H).json() if n["kind"] == "situation"]
    assert any("PVA" in n["title_de"] for n in inbox)
    steps = client.get(f"/api/cases/{case['id']}", headers=H).json()["steps"]
    assert any(s["id"].startswith("sit-") for s in steps)
    events = client.get("/api/audit", headers=auth("anna")).json()
    assert any(e["path"].endswith(f"/api/cases/{case['id']}/steps") and e["via"] == "service:situation" for e in events)
