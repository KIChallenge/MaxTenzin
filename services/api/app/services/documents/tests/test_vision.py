"""Photo uploads: type sniffing, multi-page, offline fake mode, stubbed live vision -> unchanged trust pipeline.

Images are rendered in the test with fictional text (PIL); no real document or photo is ever committed.
"""

import io
import uuid

import pytest
from PIL import Image, ImageDraw

from app.services.documents import extract, storage, vision
from app.tests.conftest import auth

H = auth("maria", "anna")
REAL = "Mobile Hauskrankenpflege zur Unterstützung bei pflegerischen Aufgaben."
FAKE = "Eine Kur in Bad Gastein wird dringend empfohlen."
CLIN = "Kontrolle des Blutbildes und der Nierenfunktion nach ärztlicher Festlegung."
TRANSCRIPT = ("Klinikum Musterstadt\nKrankenhaus-Entlassungsbefund\nEntlassungsdatum: 29.10.2026\n"
              "Empfohlen werden:\nMobile Hauskrankenpflege zur Unterstützung bei\npflegerischen Aufgaben.\n"
              "Kontrolle des Blutbildes und der Nierenfunktion\nnach ärztlicher Festlegung.\n[unleserlich] Stempel")


def make_image(fmt="PNG", size=(1600, 2200), text="Testdokument") -> bytes:
    """Synthetic page with fictional text; a random token makes every image (and its cache key) unique."""
    img = Image.new("RGB", size, "white")
    ImageDraw.Draw(img).text((40, 40), f"{text} {uuid.uuid4().hex}", fill="black")
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


@pytest.fixture(autouse=True)
def tmp_uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "uploads_dir", lambda: tmp_path)


def up(client, *imgs: bytes, field="file", name="foto.png", mime="image/png"):
    if field == "file":
        return client.post("/api/documents", headers=H, files={"file": (name, imgs[0], mime)})
    return client.post("/api/documents", headers=H,
                       files=[("files", (f"seite{i}.png", b, mime)) for i, b in enumerate(imgs, 1)])


class _Msg:
    def __init__(self, content):
        self.content = content


class _LiveVision:
    """Stub of the live LLM: chat() = vision transcription, json() = extraction (incl. a fabricated quote)."""
    live = True

    def __init__(self, text=TRANSCRIPT, fail=False):
        self.text, self.fail, self.calls = text, fail, []

    def chat(self, messages, tools=None, **kw):
        if self.fail:
            raise RuntimeError("provider down")
        self.calls.append((messages, kw))
        return _Msg(self.text)

    def json(self, system, user, max_tokens=4096):
        assert "=== Seite 1 ===" in user and "pflegerischen Aufgaben" in user
        return {"person": {}, "open_tasks": [], "recommendations": [
            {"text_de": "Im Dokument wird mobile Pflege empfohlen.", "quote": REAL, "page": 1, "category": "care"},
            {"text_de": "Erfunden.", "quote": FAKE, "page": 1, "category": "rehabilitation"},
            {"text_de": "Labor.", "quote": CLIN, "page": 1, "category": "follow_up"},
        ]}


def live(monkeypatch, llm):
    monkeypatch.setattr(vision, "get_llm", lambda: llm)
    monkeypatch.setattr(extract, "get_llm", lambda: llm)
    return llm


# --- type sniffing / rejection --------------------------------------------------------------------------

def test_media_type_is_sniffed_from_bytes():
    assert vision.media_type(b"%PDF-1.7") == vision.PDF
    assert vision.media_type(make_image("JPEG")) == vision.JPEG
    assert vision.media_type(make_image("PNG")) == vision.PNG
    assert vision.media_type(b"\x00\x00\x00\x18ftypheic\x00\x00") == vision.HEIC
    assert vision.media_type(b"GIF89a") is None


def test_heic_and_unknown_types_get_clear_415(client):
    r = up(client, b"\x00\x00\x00\x18ftypheic" + b"\x00" * 64, name="IMG_0001.HEIC", mime="image/heic")
    assert r.status_code == 415 and "JPG oder PNG" in r.json()["detail"]
    r = up(client, b"GIF89a....", name="x.gif", mime="image/gif")
    assert r.status_code == 415 and "JPG oder PNG" in r.json()["detail"]


def test_broken_image_and_mixed_or_too_many_files_are_rejected(client):
    r = up(client, b"\xff\xd8\xff\xe0 kaputt", name="kaputt.jpg", mime="image/jpeg")
    assert r.status_code == 415 and "konnte nicht gelesen werden" in r.json()["detail"]
    mixed = client.post("/api/documents", headers=H, files=[("files", ("a.pdf", b"%PDF-1.4 x", "application/pdf")),
                                                             ("files", ("b.png", make_image(), "image/png"))])
    assert mixed.status_code == 415
    assert up(client, *[make_image(size=(50, 50))] * 11, field="files").status_code == 413
    assert client.post("/api/documents", headers=H).status_code == 422


# --- offline (no key): deterministic, error-free, empty --------------------------------------------------

def test_photo_upload_offline_is_fake_and_empty(client):
    img = make_image("JPEG")
    doc = up(client, img, name="brief.jpg", mime="image/jpeg").json()
    assert doc["owner_id"] == "anna" and doc["doc_type"] == "other"
    t = client.get(f"/api/documents/{doc['document_id']}/transcript", headers=H).json()
    assert t["mode"] == "fake" and t["source"] == "image" and [p["text"] for p in t["pages"]] == [""]
    a = client.post(f"/api/documents/{doc['document_id']}/analyze", headers=H).json()
    assert a["extraction_mode"] == "fake" and a["recommendations"] == [] and a["pages"] == 1
    assert "Aus einem Foto gelesen" in a["notice_de"]
    f = client.get(f"/api/documents/{doc['document_id']}/file", headers=H)
    assert f.status_code == 200 and f.headers["content-type"] == "image/jpeg" and f.content == img


def test_multiple_photos_become_pages(client):
    a, b = make_image(), make_image()
    doc = up(client, a, b, field="files").json()
    assert "(+1 Fotos)" in doc["filename"]
    t = client.get(f"/api/documents/{doc['document_id']}/transcript", headers=H).json()
    assert [p["page"] for p in t["pages"]] == [1, 2]
    assert client.get(f"/api/documents/{doc['document_id']}/file?page=2", headers=H).content == b
    assert client.get(f"/api/documents/{doc['document_id']}/file?page=3", headers=H).status_code == 404
    assert client.get(f"/api/documents/{doc['document_id']}/transcript", headers=auth("stefan")).status_code == 404


def test_low_resolution_is_flagged():
    t = vision.transcribe("d", [make_image(size=(595, 842)), make_image()])
    assert [p.low_resolution for p in t.pages] == [True, False]


# --- live vision (stubbed): same trust pipeline as PDFs -------------------------------------------------

def test_vision_pipeline_verifies_quotes_filters_clinical_and_reads_facts(client, monkeypatch):
    llm = live(monkeypatch, _LiveVision())
    doc = up(client, make_image("JPEG"), name="IMG_1234.jpg", mime="image/jpeg").json()
    assert doc["doc_type"] == "discharge_letter"          # detected from the transcript, not the filename
    messages, kw = llm.calls[0]
    assert kw["reasoning_effort"] == "low"
    assert messages[1]["content"][1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert "WÖRTLICH" in messages[0]["content"] and "[unleserlich]" in messages[0]["content"]

    a = client.post(f"/api/documents/{doc['document_id']}/analyze", headers=H).json()
    assert a["extraction_mode"] == "vision"
    assert [r["quote"] for r in a["recommendations"]] == [REAL]   # fabricated dropped, clinical filtered
    assert a["dropped_unverified"] == 1 and "Medikation" in a["notice_de"]
    assert "Aus einem Foto gelesen – bitte prüfen Sie die übernommenen Angaben." in a["notice_de"]
    assert {f["key"]: f["value"] for f in a["facts"]}["discharge_date"] == "29.10.2026"

    t = client.get(f"/api/documents/{doc['document_id']}/transcript", headers=H).json()
    assert t["mode"] == "vision" and t["pages"][0]["text"] == TRANSCRIPT and t["pages"][0]["unreadable"] == 1
    again = client.post(f"/api/documents/{doc['document_id']}/analyze", headers=H).json()
    assert again["extraction_mode"] == "vision-cached" and again["recommendations"] == a["recommendations"]
    assert len(llm.calls) == 1                             # transcript stored, not re-read


def test_same_photo_uploaded_twice_is_read_once(client, monkeypatch):
    llm = live(monkeypatch, _LiveVision())
    img = make_image()
    up(client, img)
    doc = up(client, img).json()
    assert len(llm.calls) == 1
    t = client.get(f"/api/documents/{doc['document_id']}/transcript", headers=H).json()
    assert t["mode"] == "vision-cached"


def test_vision_failure_is_retried_on_analyze(client, monkeypatch):
    live(monkeypatch, _LiveVision(fail=True))
    doc = up(client, make_image()).json()
    assert doc["doc_type"] == "other"
    assert client.post(f"/api/documents/{doc['document_id']}/analyze", headers=H).status_code == 502
    live(monkeypatch, _LiveVision())
    a = client.post(f"/api/documents/{doc['document_id']}/analyze", headers=H).json()
    assert a["extraction_mode"] == "vision" and a["doc_type"] == "discharge_letter"
    listed = {d["document_id"]: d for d in client.get("/api/documents", headers=H).json()}
    assert listed[doc["document_id"]]["doc_type"] == "discharge_letter"


def test_pdf_transcript_is_the_text_layer(client):
    from app.services.documents.tests.test_documents import DISCHARGE

    doc = client.post("/api/documents", headers=H, files={"file": ("b.pdf", DISCHARGE, "application/pdf")}).json()
    t = client.get(f"/api/documents/{doc['document_id']}/transcript", headers=H).json()
    assert t["mode"] == "pdf-text" and len(t["pages"]) == 2 and "Entlassungsbefund" in t["pages"][0]["text"]
    assert client.get("/api/documents/doc-anna-entlassung/transcript", headers=H).status_code == 404
