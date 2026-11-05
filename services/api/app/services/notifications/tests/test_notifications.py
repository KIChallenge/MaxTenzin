from app.conftest import auth


def test_prevention_notifications_for_self(client):
    items = client.get("/api/notifications", headers=auth("stefan")).json()
    assert any(n["kind"] == "prevention" for n in items)


def test_scopes_apply_transitively(client):
    # Anna did not grant Maria view_health_prevention -> no prevention notifications, but case notifications
    client.post("/api/cases", headers=auth("maria", "anna"), json={"subject_id": "anna", "title_de": "Nach dem Spital",
                                                                    "document_id": "doc-anna-entlassung"})
    items = client.get("/api/notifications", headers=auth("maria", "anna")).json()
    assert items and all(n["kind"] != "prevention" for n in items)
    assert any(n["kind"] == "case" for n in items)


def test_mark_read(client):
    n = client.get("/api/notifications", headers=auth("stefan")).json()[0]
    client.post(f"/api/notifications/{n['id']}/read", headers=auth("stefan"))
    again = next(x for x in client.get("/api/notifications", headers=auth("stefan")).json() if x["id"] == n["id"])
    assert again["read"] is True
