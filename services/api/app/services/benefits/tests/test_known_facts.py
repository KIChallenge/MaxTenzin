"""Answers to open questions are stored per subject and shared by cockpit and Lotsi."""

from app.conftest import auth

H = auth("maria", "anna")


def test_known_facts_roundtrip_and_used_in_eligibility(client):
    assert client.get("/api/benefits/facts", headers=H).status_code == 200
    r = client.patch("/api/benefits/facts", headers=H, json={"facts": {"walking_unable_confirmed": True, "as_of": "x"}})
    data = r.json()
    assert data["facts"] == {"walking_unable_confirmed": True}
    assert "Maria Berger" in data["sources"]["walking_unable_confirmed"]["label"]
    assert "Cockpit" in data["sources"]["walking_unable_confirmed"]["label"]
    res = client.post("/api/benefits/eligibility", headers=H,
                      json={"subject_id": "anna", "benefit_ids": ["krankentransport"]}).json()
    assert "walking_unable_confirmed" not in res[0]["missing_fields"]
    client.patch("/api/benefits/facts", headers=H, json={"facts": {"walking_unable_confirmed": None}})
    assert client.get("/api/benefits/facts", headers=H).json()["facts"] == {}
    assert client.get("/api/benefits/facts", headers=auth("stefan", "anna")).status_code == 403
