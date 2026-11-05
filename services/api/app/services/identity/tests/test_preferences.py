"""Preferences are stored per acting person and returned (regression: endpoints were missing once)."""

from app.conftest import auth


def test_preferences_roundtrip(client):
    assert client.get("/api/identity/preferences", headers=auth("stefan")).json()["detail"] == "normal"
    r = client.put("/api/identity/preferences", headers=auth("stefan"), json={"detail": "short", "daypart": "morning"})
    assert r.status_code == 200
    got = client.get("/api/identity/preferences", headers=auth("stefan")).json()
    assert got["detail"] == "short" and got["daypart"] == "morning"
    client.put("/api/identity/preferences", headers=auth("stefan"), json={})
