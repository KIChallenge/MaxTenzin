"""Golden checks against the real (fictional) demo PDFs. Skipped automatically when docs/ is absent.

Run locally: RAW_DATA_DIR=/path/to/docs make test-api
"""

from pathlib import Path

import pytest

from app.contracts.documents import DocumentType
from app.core.config import get_settings
from app.services.documents import goldens
from app.services.documents.extract import analyze_pdf
from app.services.documents.pdf import detect_doc_type, page_texts, sha256
from app.services.documents.verify import quote_on_page
from app.services.prevention.impfpass import parse_impfpass

BEFUNDE = Path(get_settings().raw_data_dir) / "Befunde"
NAMES = ["Entlassungsbefund.pdf", "Impfpass.pdf", "Röntgen Befund.pdf", "Röntgen Befund2.pdf",
         "Befund bildgebende Diagnostik.pdf"]

pytestmark = pytest.mark.skipif(not (BEFUNDE / "Entlassungsbefund.pdf").exists(),
                                reason="raw demo PDFs (docs/Befunde) not available")


@pytest.mark.parametrize("name", NAMES)
def test_golden_matches_pdf(name):
    data = (BEFUNDE / name).read_bytes()
    pages = page_texts(data)
    g = goldens.by_sha(sha256(data))
    assert g is not None, f"no golden for {name}"
    assert g["analysis"]["pages"] == len(pages)
    assert detect_doc_type(pages, name) == DocumentType(g["analysis"]["doc_type"])
    for r in g["analysis"]["recommendations"]:
        assert quote_on_page(r["quote"], r["page"], pages), (r["id"], r["quote"])
    a = analyze_pdf("doc-x", name, sha256(data), detect_doc_type(pages, name), pages)
    assert len(a.recommendations) == len(g["analysis"]["recommendations"])  # nothing dropped


def test_impfpass_parser_matches_golden():
    data = (BEFUNDE / "Impfpass.pdf").read_bytes()
    got = [v.model_dump() for v in parse_impfpass(page_texts(data))]
    assert got == goldens.by_sha(sha256(data))["vaccinations"]
    assert sum(v["disease"] == "COVID-19" for v in got) == 5
    assert sorted(v["date"] for v in got if v["disease"] == "Influenza") == [
        "2021-11-17", "2023-11-22", "2024-11-06", "2025-11-03"]
