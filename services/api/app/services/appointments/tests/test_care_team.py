"""Behandlungsteam: seeded Hausärztin, change by the person, own-GP slot search."""

from app.conftest import auth

H = auth("maria", "anna")


def test_care_team_and_own_gp_slots(client):
    team = client.get("/api/identity/care-team", headers=H).json()
    gp = next(m for m in team["members"] if m["role"] == "hausarzt")
    assert gp["provider_id"] == "demo-gp-1030-muster" and "Demo" in gp["name"]
    slots = client.post("/api/appointments/slots/search", headers=H, json={"provider_id": gp["provider_id"], "limit": 5}).json()
    assert len(slots) == 5 and {s["provider"]["id"] for s in slots} == {"demo-gp-1030-muster"}
    team2 = client.put("/api/identity/care-team", headers=H, json={"role": "hausarzt", "provider_id": "demo-gp-1020-probe"}).json()
    gp2 = next(m for m in team2["members"] if m["role"] == "hausarzt")
    assert gp2["provider_id"] == "demo-gp-1020-probe" and gp2["source"]["label"].startswith("Angabe von Maria Berger")
    assert client.get("/api/identity/care-team", headers=auth("stefan", "anna")).status_code == 403
