"""Lebenslage facts feed eligibility; document sources carry the document id."""

from app.conftest import auth

H = auth("maria", "anna")


def test_confirmed_therapy_feeds_transport_rules_and_doc_refs(client):
    ep = client.post("/api/situation/episodes", headers=H, json={"type": "therapy", "subtype": "strahlentherapie",
                                                                 "start": "2026-10-01"}).json()
    assert ep["status"] in ("active", "planned")
    res = client.post("/api/benefits/eligibility", headers=H,
                      json={"subject_id": "anna", "document_ids": ["doc-anna-entlassung"],
                            "benefit_ids": ["fahrtkostenzuschuss", "pflegegeld"]}).json()
    fk = next(r for r in res if r["benefit"]["id"] == "fahrtkostenzuschuss")
    assert "treatment_type" not in fk["missing_fields"]
    refs = [c["source"]["ref"] for r in res for c in r["criteria"] if c.get("source") and c["source"]["kind"] == "document"]
    assert refs and all(x.startswith("document:doc-anna-entlassung#page=") for x in refs)
    client.delete(f"/api/situation/episodes/{ep['id']}", headers=H)
