"""prevention: e-Impfpass parser, rule engine (goldens for Stefan + Anna), wording rule, sources, endpoints."""

import json
from datetime import date

import pytest

from app.contracts.common import SourceKind
from app.contracts.prevention import VaccinationEntry
from app.core.knowledge import kpath
from app.seed.loader import get_person
from app.services.documents import goldens, storage
from app.services.documents.pdf import normalize
from app.services.prevention.engine import evaluate, knowledge
from app.services.prevention.impfpass import parse_impfpass
from app.tests.conftest import auth

AS_OF = date(2026, 11, 5)
STEFAN_VACCS = [VaccinationEntry(**v) for v in goldens.by_demo_id("doc-stefan-impfpass")["vaccinations"]]

SYNTHETIC_IMPFPASS = """Elektronischer Impfpass
e-Impfpass
Einträge
Influenza ('echte Grippe')
3. Nov. 2025
 Impfstoff: INFLUVAC TRI FSPR 0,5ML O.K.
Impfdatum: 3. November 2025
Auffrischung
 Impfort: Heinestraße 11/12
1020 Wien, Wien
Diphtherie, Tetanus, Pertussis, Poliomyelitis
12. Mai 2019
 Impfstoff: BOOSTRIX POLIO
Impfdatum: 12. Mai 2019 um 10:00 Uhr (UTC+2)
Auffrischung
 Impfort: Teststraße 1
1120 Wien, 00
"""


@pytest.fixture(autouse=True)
def tmp_uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "uploads_dir", lambda: tmp_path)


def by_id(items):
    return {i.id: i for i in items}


# --- parser ---------------------------------------------------------------------------------------------

def test_parser_synthetic_layout_incl_combined_vaccine():
    got = parse_impfpass([SYNTHETIC_IMPFPASS])
    assert [(v.disease, v.date, v.dose_label, v.place) for v in got] == [
        ("Influenza", "2025-11-03", "Auffrischung", "1020 Wien"),
        ("Diphtherie-Tetanus-Pertussis-Polio", "2019-05-12", "Auffrischung", "1120 Wien"),
    ]


def test_stefan_golden_vaccinations():
    assert sum(v.disease == "COVID-19" for v in STEFAN_VACCS) == 5
    assert sorted(v.date for v in STEFAN_VACCS if v.disease == "Influenza") == [
        "2021-11-17", "2023-11-22", "2024-11-06", "2025-11-03"]


# --- engine goldens -------------------------------------------------------------------------------------

def test_stefan_golden_as_of_2026_11_05():
    golden = json.loads((goldens.GOLDENS_DIR / "prevention_stefan_2026-11-05.json").read_text(encoding="utf-8"))
    items = by_id(evaluate(get_person("stefan"), STEFAN_VACCS, AS_OF)[0])
    assert {k: v.status.value for k, v in items.items()} == golden["expected_status"]
    assert items["influenza"].last_date == "2025-11-03"


def test_anna_free_zoster_and_pneumo_shown_as_info():
    items = by_id(evaluate(get_person("anna"), [], AS_OF)[0])
    for rid in ("herpes_zoster", "pneumococcal"):
        assert items[rid].status == "not_documented" and "kostenlos" in items[rid].cost_de
        assert items[rid].sources[0].label == "ÖGK Serviceratgeber 2026, S. 32"
    assert "mammografie" in items and items["mammografie"].status == "not_documented"  # 78: opt-in only
    assert "covid19" in items  # >= 60


def test_seasonal_and_interval_logic():
    stefan = get_person("stefan")
    flu_now = [VaccinationEntry(disease="Influenza", date="2026-10-10", vaccine="X")]
    assert by_id(evaluate(stefan, flu_now, AS_OF)[0])["influenza"].status == "up_to_date"
    # June 2026: the 2025/26 dose still covers the season that ended -> up_to_date
    assert by_id(evaluate(stefan, STEFAN_VACCS, date(2026, 6, 1))[0])["influenza"].status == "up_to_date"
    old = [VaccinationEntry(disease="Influenza", date="2024-11-06", vaccine="X")]
    summer = by_id(evaluate(stefan, old, date(2026, 6, 1))[0])["influenza"]
    assert summer.status == "upcoming" and summer.due_date == "2026-10-01"
    dtp = [VaccinationEntry(disease="Diphtherie-Tetanus-Pertussis-Polio", date="2017-01-01", vaccine="X")]
    assert by_id(evaluate(stefan, dtp, AS_OF)[0])["dtp_polio"].status == "upcoming"   # due 2027-01-01
    assert by_id(evaluate(stefan, dtp, date(2027, 2, 1))[0])["dtp_polio"].status == "due"
    anna_dtp = [VaccinationEntry(disease="Tetanus", date="2020-01-01", vaccine="X")]
    assert by_id(evaluate(get_person("anna"), anna_dtp, AS_OF)[0])["dtp_polio"].status == "due"  # 60+: 5 years


def test_child_gets_programme_info_only():
    items = by_id(evaluate(get_person("lena"), [], AS_OF)[0])
    assert set(items) == {"kinderimpfprogramm"}


def test_wording_never_fehlt_and_always_sourced():
    for pid in ("stefan", "anna", "lena", "maria"):
        for i in evaluate(get_person(pid), STEFAN_VACCS if pid == "stefan" else [], AS_OF)[0]:
            assert "fehl" not in i.explanation_de.lower() and "fehl" not in i.title_de.lower()
            assert i.sources, i.id
            if i.status == "not_documented" and i.kind == "vaccination":
                assert "nicht im e-Impfpass dokumentiert – bitte mit Ihrer Ärztin bzw. Ihrem Arzt klären" in i.explanation_de and "Ärztin bzw." in i.explanation_de


def test_external_sources_marked_with_url_and_retrieval_date():
    srcs = knowledge()["sources"]
    ext = [s for s in srcs.values() if s["kind"] == "external"]
    assert ext and all(s["url"].startswith("https://") and s["retrieved"] == "2026-11-05" for s in ext)
    flu = by_id(evaluate(get_person("stefan"), [], AS_OF)[0])["influenza"]
    e = next(s for s in flu.sources if s.kind == SourceKind.external)
    assert e.ref == "https://www.sozialministerium.gv.at/impfplan" and "abgerufen am 05.11.2026" in e.label


def test_brochure_quotes_are_verbatim_in_serviceratgeber():
    pages = {}
    for line in kpath("extracted/serviceratgeber/pages.jsonl").read_text(encoding="utf-8").splitlines():
        p = json.loads(line)
        pages.setdefault(p["printed_page"], "")
        pages[p["printed_page"]] += "\n" + p["text"]
    for key, s in knowledge()["sources"].items():
        if s["kind"] == "brochure":
            assert normalize(s["quote"]) in normalize(pages[s["page"]]), key


# --- endpoints ------------------------------------------------------------------------------------------

def test_overview_without_import_is_not_documented(client):
    r = client.get("/api/prevention/overview", params={"as_of": "2026-11-05"}, headers=auth("anna"))
    items = by_id_json(r.json()["items"])
    assert r.json()["vaccinations"] == [] and items["influenza"]["status"] == "not_documented"


def by_id_json(items):
    return {i["id"]: i for i in items}


def test_import_demo_impfpass_then_overview(client):
    h = auth("stefan")
    r = client.post("/api/prevention/import/doc-stefan-impfpass", params={"as_of": "2026-11-05"}, headers=h)
    assert r.status_code == 200 and len(r.json()["vaccinations"]) == 9
    ov = client.get("/api/prevention/overview", params={"as_of": "2026-11-05"}, headers=h).json()
    items = by_id_json(ov["items"])
    assert items["influenza"]["status"] == "due" and items["dtp_polio"]["status"] == "not_documented"
    assert "Hinweise laut" in ov["disclaimer_de"]


def test_import_uploaded_pdf_and_reject_non_impfpass(client):
    from app.services.documents.tests.test_documents import make_pdf

    h = auth("maria")
    lines = SYNTHETIC_IMPFPASS.splitlines()
    doc = client.post("/api/documents", headers=h, files={"file": ("impfpass.pdf", make_pdf([lines]), "application/pdf")}).json()
    assert doc["doc_type"] == "vaccination_record"
    r = client.post(f"/api/prevention/import/{doc['document_id']}", params={"as_of": "2026-11-05"}, headers=h)
    assert r.status_code == 200
    items = by_id_json(r.json()["items"])
    assert items["dtp_polio"]["status"] == "up_to_date" and items["influenza"]["status"] == "due"
    other = client.post("/api/documents", headers=h,
                        files={"file": ("x.pdf", make_pdf([["Rechnung Nr. 4711"]]), "application/pdf")}).json()
    assert client.post(f"/api/prevention/import/{other['document_id']}", headers=h).status_code == 422
    assert client.post("/api/prevention/import/doc-stefan-impfpass", headers=h).status_code == 404  # not Maria's


def test_import_requires_scope(client):
    assert client.post("/api/prevention/import/doc-stefan-impfpass", headers=auth("maria", "anna")).status_code == 403
