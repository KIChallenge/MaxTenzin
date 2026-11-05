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
    # steps go to Anna's most recent case (other tests may have created cases in the same second)
    cases = client.get("/api/cases", headers=H).json()
    assert any(st["id"].startswith("sit-") for c in cases for st in c["steps"])
    events = client.get("/api/audit", headers=auth("anna")).json()
    assert any(e["path"].endswith("/steps") and e["via"] == "service:situation" for e in events)
    assert case["id"]


def test_second_copy_of_document_does_not_duplicate_suggestions(client):
    from app.core.db import store

    first = client.post("/api/situation/suggestions/from-document/doc-anna-entlassung", headers=H).json()
    # a second copy of the SAME letter (e.g. photo + PDF) yields the same analysis content
    original = client.get("/api/documents/doc-anna-entlassung/analysis", headers=H).json()
    store.put("document_analyses", "doc-anna-copy", {**original, "document_id": "doc-anna-copy"}, subject_id="anna")
    second = client.post("/api/situation/suggestions/from-document/doc-anna-copy", headers=H).json()
    assert {e["id"] for e in second} <= {e["id"] for e in first} | {e["id"] for e in second if e["status"] != "suggested"}
    overview = client.get("/api/situation", headers=H).json()
    types = [e["type"] for e in overview["suggestions"]]
    assert len(types) == len(set(types))
