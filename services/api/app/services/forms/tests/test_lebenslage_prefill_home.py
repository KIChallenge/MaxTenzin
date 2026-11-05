"""PAL 080: Lebenslage 'zu Hause mit Unterstützung' answers 'Betreuung' and the temporary-stay question."""

from app.conftest import auth

H = auth("maria", "anna")


def test_home_care_prefills_help_and_blank_temporary_stay(client):
    ep = client.post("/api/situation/episodes", headers=H, json={"type": "home_care"}).json()
    try:
        s = client.post("/api/forms/definitions/pva_pflegegeld_pal080/sessions", headers=H).json()
        v = s["values"]
        assert v["Betreuung durch andere Person"]["value"] == "ja" and v["Betreuung durch andere Person"]["source"]
        assert v["voruebergehend"]["value"] == "" and v["voruebergehend"]["source"]   # known: leave empty
        nq = client.get(f"/api/forms/sessions/{s['id']}/next-questions?include_optional=true", headers=H).json()
        asked = {q["id"] for q in nq["questions"]}
        assert "voruebergehend" not in asked and "Betreuung durch andere Person" not in asked
    finally:
        client.delete(f"/api/situation/episodes/{ep['id']}", headers=H)


def test_without_lebenslage_both_are_still_asked(client):
    s = client.post("/api/forms/definitions/pva_pflegegeld_pal080/sessions", headers=H).json()
    nq = client.get(f"/api/forms/sessions/{s['id']}/next-questions?include_optional=true", headers=H).json()
    asked = {q["id"] for q in nq["questions"]}
    assert {"voruebergehend", "Betreuung durch andere Person"} <= asked
