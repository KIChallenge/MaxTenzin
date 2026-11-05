"""Deterministic document facts (Entlassungsdatum) flow into the official form with quote + page."""

from app.conftest import auth
from app.contracts.documents import DocumentFact
from app.fixtures import ANNA_ANALYSIS

H = auth("maria", "anna")


def test_discharge_date_prefilled_with_quote(client):
    from app.core.db import store

    a = ANNA_ANALYSIS.model_copy(update={"document_id": "doc-test-facts", "facts": [
        DocumentFact(key="discharge_date", value="29.10.2026", quote="Entlassungsdatum 29.10.2026", page=1)]})
    store.put("document_analyses", a.document_id, a.model_dump(), subject_id="anna")
    s = client.post("/api/forms/definitions/pva_pflegegeld_pal080/sessions", params={"document_id": a.document_id},
                    headers=H).json()
    assert s["document_id"] == "doc-test-facts"
    kh = s["values"]["KH bis"]
    assert kh["value"] == "29.10.2026" and kh["source"]["quote"] == "Entlassungsdatum 29.10.2026"
    assert kh["source"]["label"].endswith("S. 1") and kh["confirmed"] is False
    ids = [q["id"] for q in client.get(f"/api/forms/sessions/{s['id']}/next-questions", headers=H).json()["questions"]]
    assert "KH bis" not in ids and "KH von" in ids and "Spital" in ids


def test_imaging_report_has_no_facts():
    from app.contracts.documents import DocumentType
    from app.services.documents.facts import admin_facts

    assert admin_facts(DocumentType.imaging_report, ["Entlassungsdatum 01.01.2026\n"]) == []
