import re

from app.services.medications import service
from app.tests.conftest import auth

FORBIDDEN = re.compile(r"(?i)\b(dosis|dosierung von|nehmen sie|einnehmen sollten|empfehle)\b")


def test_detail_endpoint(client):
    h = auth("anna")
    m = client.get("/api/medications/0001063", headers=h).json()
    assert m["name"].startswith("Agaffin") and m["source"]["kind"] == "eko"
    assert "3,85 €" in m["patient_cost_note_de"] and "Höchstens 2 Packung" in m["patient_cost_note_de"]
    assert client.get("/api/medications/1063", headers=h).json()["pharma_nr"] == "0001063"   # zero-padded
    assert client.get("/api/medications/9999999", headers=h).status_code == 404
    assert client.get("/api/medications/abc", headers=h).status_code == 422


def test_restriction_wording_is_administrative():
    assert "chef-/kontrollärztlichen" in service.approval_text("Y", "RE1")
    assert "Anwendungsgebiete" in service.approval_text("G", "IND")
    assert service.approval_text("G", "") == "Grüner Bereich – frei verschreibbar."
    assert "Weitere Einschränkung" in service.approval_text("G", "N P")
    assert set(service.APPROVAL) <= service.legend_codes()
    for m in service.search("Amlodipin", 50):
        assert not FORBIDDEN.search(m.approval_needed_de + m.patient_cost_note_de)


def test_search_prefix_first():
    res = service.search("amlo", 5)
    assert res and res[0].name.lower().startswith("amlo")
    assert service.search("   ") == []


def test_search_tokens_when_no_substring_hit():
    # people type 'Pantoprazol 20 mg' / '20mg'; EKO names read 'Pantoprazol "Sandoz" 20 mg magensaftresistente Tabl.'
    for q in ("Pantoprazol 20 mg", "pantoprazol 20mg"):
        hits = service.search(q, 10)
        assert hits and all("pantoprazol" in m.name.lower() and "20 mg" in m.name.lower() for m in hits), q
    assert service.search("Pantoprazol 999 mg", 10) == []
