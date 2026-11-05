"""documents: upload, doc-type detection, quote verification (anti-hallucination), golden + live paths. No docs/ needed."""

import io

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.contracts.documents import DocumentType, Recommendation
from app.services.documents import extract, goldens, storage
from app.services.documents.pdf import detect_doc_type, page_texts
from app.services.documents.verify import quote_on_page, verify_recommendations
from app.tests.conftest import auth

MARIA_FOR_ANNA = auth("maria", "anna")
REAL = "Mobile Hauskrankenpflege zur Unterstützung bei pflegerischen Aufgaben."
FAKE = "Eine Kur in Bad Gastein wird dringend empfohlen."


def make_pdf(pages: list[list[str]]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    for lines in pages:
        y = 800
        for ln in lines:
            c.drawString(50, y, ln)
            y -= 16
        c.showPage()
    c.save()
    return buf.getvalue()


DISCHARGE = make_pdf([
    ["Krankenhaus-Entlassungsbefund", "Name Anna Berger"],
    ["Empfohlen werden:", "Mobile Hauskrankenpflege zur Unterstützung bei", "pflegerischen Aufgaben."],
])


@pytest.fixture(autouse=True)
def tmp_uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "uploads_dir", lambda: tmp_path)


def rec(id: str, quote: str, page: int) -> Recommendation:
    return Recommendation(id=id, text_de="Im Dokument wird … empfohlen.", quote=quote, page=page, category="care")


# --- quote verification ---------------------------------------------------------------------------------

def test_quote_verification_drops_fabricated_quote():
    pages = page_texts(DISCHARGE)
    kept, dropped = verify_recommendations([rec("ok", REAL, 2), rec("fake", FAKE, 2)], pages)
    assert [r.id for r in kept] == ["ok"] and dropped == ["fake"]


def test_quote_must_be_on_stated_page_and_not_trivial():
    pages = page_texts(DISCHARGE)
    assert quote_on_page(REAL, 2, pages)
    assert not quote_on_page(REAL, 1, pages)          # right text, wrong page
    assert not quote_on_page(REAL, 9, pages)          # page out of range
    assert not quote_on_page("Mobile", 2, pages)      # too short to count as evidence
    assert quote_on_page("Mobile   Hauskrankenpflege\nzur Unterstützung", 2, pages)  # whitespace-normalised


def test_quote_verification_handles_hyphenated_line_breaks():
    pages = ["Med. verantwortl. Person: Dr. Claudia Kap-\npel und weitere Personen"]
    assert quote_on_page("Dr. Claudia Kappel und weitere", 1, pages)


# --- doc type detection ---------------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("Krankenhaus-Entlassungsbefund\nEntlassungsdatum 29.10.2026", DocumentType.discharge_letter),
    ("Befund Bildgebende Diagnostik\nVorfußröntgen", DocumentType.imaging_report),
    ("US-Befund\nSonographie Becken links", DocumentType.imaging_report),
    ("Elektronischer Impfpass\nImpfstoff: X", DocumentType.vaccination_record),
    ("Rechnung Nr. 4711", DocumentType.other),
])
def test_detect_doc_type(text, expected):
    assert detect_doc_type([text]) == expected


# --- endpoints ------------------------------------------------------------------------------------------

def upload(client, data: bytes, name="brief.pdf", headers=MARIA_FOR_ANNA):
    return client.post("/api/documents", headers=headers, files={"file": (name, data, "application/pdf")})


def test_upload_detects_type_lists_and_streams_file(client):
    r = upload(client, DISCHARGE)
    assert r.status_code == 200
    doc = r.json()
    assert doc["doc_type"] == "discharge_letter" and doc["owner_id"] == "anna"
    assert any(d["document_id"] == doc["document_id"] for d in client.get("/api/documents", headers=MARIA_FOR_ANNA).json())
    f = client.get(f"/api/documents/{doc['document_id']}/file", headers=MARIA_FOR_ANNA)
    assert f.status_code == 200 and f.headers["content-type"] == "application/pdf" and f.content == DISCHARGE


def test_upload_rejects_non_pdf(client):
    assert upload(client, b"hello", name="x.txt").status_code == 415


def test_other_subject_cannot_read_document(client):
    doc = upload(client, DISCHARGE).json()
    assert client.get(f"/api/documents/{doc['document_id']}/file", headers=auth("stefan")).status_code == 404
    assert client.post(f"/api/documents/{doc['document_id']}/analyze", headers=auth("stefan")).status_code == 404


def test_analyze_without_golden_offline_returns_empty_fake(client):
    doc = upload(client, DISCHARGE).json()
    a = client.post(f"/api/documents/{doc['document_id']}/analyze", headers=MARIA_FOR_ANNA).json()
    assert a["extraction_mode"] == "fake" and a["recommendations"] == [] and a["pages"] == 2


def test_golden_path_drops_fabricated_quote_and_stores_analysis(client, monkeypatch):
    fake_golden = {"sha256": "x", "analysis": {
        "filename": "golden.pdf", "doc_type": "discharge_letter", "pages": 2, "person": {"first_name": "Anna"},
        "recommendations": [rec("r1", REAL, 2).model_dump(), rec("r2", FAKE, 2).model_dump()],
        "open_tasks": ["Mobile Hauskrankenpflege organisieren"]}}
    monkeypatch.setattr(goldens, "by_sha", lambda sha: fake_golden)
    doc = upload(client, DISCHARGE).json()
    a = client.post(f"/api/documents/{doc['document_id']}/analyze", headers=MARIA_FOR_ANNA).json()
    assert a["extraction_mode"] == "golden" and [r["id"] for r in a["recommendations"]] == ["r1"]
    assert a["filename"] == "brief.pdf"
    got = client.get(f"/api/documents/{doc['document_id']}/analysis", headers=MARIA_FOR_ANNA).json()
    assert got == a


class _LiveLLM:
    live = True

    def json(self, system, user, max_tokens=4096):
        assert "=== Seite 2 ===" in user and "WÖRTLICHE" in system
        return {"doc_type": "discharge_letter", "person": {"first_name": "Anna", "birth_date": None},
                "recommendations": [
                    {"text_de": "Im Dokument wird mobile Pflege empfohlen.", "quote": REAL, "page": 2,
                     "category": "care", "related_benefit_ids": ["fsw_mobile_pflege", "erfunden"]},
                    {"text_de": "Erfunden.", "quote": FAKE, "page": 2, "category": "rehabilitation"},
                    {"text_de": "kaputt"},
                ], "open_tasks": ["Mobile Hauskrankenpflege organisieren"]}


def test_live_path_parses_json_and_drops_hallucinations(client, monkeypatch):
    monkeypatch.setattr(extract, "get_llm", lambda: _LiveLLM())
    doc = upload(client, DISCHARGE).json()
    a = client.post(f"/api/documents/{doc['document_id']}/analyze", headers=MARIA_FOR_ANNA).json()
    assert a["extraction_mode"] == "live"
    assert [r["quote"] for r in a["recommendations"]] == [REAL]
    assert a["recommendations"][0]["related_benefit_ids"] == ["fsw_mobile_pflege"]  # unknown ids filtered


def test_imaging_report_never_yields_recommendations(client, monkeypatch):
    monkeypatch.setattr(extract, "get_llm", lambda: _LiveLLM())  # even a live model returning recs is ignored
    img = make_pdf([["Befund Bildgebende Diagnostik", "Mobile Hauskrankenpflege zur Unterstützung bei",
                     "pflegerischen Aufgaben."], ["Empfohlen werden: nichts"]])
    doc = upload(client, img, name="roentgen.pdf").json()
    assert doc["doc_type"] == "imaging_report"
    a = client.post(f"/api/documents/{doc['document_id']}/analyze", headers=MARIA_FOR_ANNA).json()
    assert a["recommendations"] == [] and "interpretiere keine Befunde" in a["notice_de"]


def test_demo_document_served_from_golden_without_upload(client):
    a = client.post("/api/documents/doc-anna-entlassung/analyze", headers=MARIA_FOR_ANNA).json()
    assert a["document_id"] == "doc-anna-entlassung" and a["extraction_mode"] == "golden"
    assert {"r1", "r2", "r3", "r4", "r5"} <= {r["id"] for r in a["recommendations"]}
    assert client.post("/api/documents/doc-anna-entlassung/analyze", headers=auth("stefan")).status_code == 404


def test_committed_goldens_are_wellformed():
    gs = goldens.all_goldens()
    assert len(gs) >= 5
    by_name = {g["source_filename"]: g for g in gs}
    anna = by_name["Entlassungsbefund.pdf"]["analysis"]
    assert anna["doc_type"] == "discharge_letter" and len(anna["open_tasks"]) == 8
    for r in anna["recommendations"]:
        assert r["quote"] and r["page"] >= 1
        assert set(r["related_benefit_ids"]) <= extract.BENEFIT_IDS
    for name in ("Röntgen Befund.pdf", "Röntgen Befund2.pdf", "Befund bildgebende Diagnostik.pdf"):
        assert by_name[name]["analysis"]["doc_type"] == "imaging_report"
        assert by_name[name]["analysis"]["recommendations"] == []
