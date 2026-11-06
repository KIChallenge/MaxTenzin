"""Pins extracted knowledge to known facts. Runs WITHOUT docs/ (reads only committed knowledge/extracted)."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EX = ROOT / "knowledge" / "extracted"


def _jsonl(p):
    return [json.loads(line) for line in (EX / p).read_text(encoding="utf-8").splitlines()]


def _value(key, year=2026):
    vals = json.loads((EX / "values/veraendw.json").read_text(encoding="utf-8"))["values"]
    return next(v["value"] for v in vals if v["key"] == key and v["year"] == year)


def test_pflegegeld_2026_values():
    assert _value("pflegegeld_stufe_1") == 206.20
    assert _value("pflegegeld_stufe_3") == 592.60
    assert _value("pflegegeld_stufe_7") == 2214.80


def test_rezeptgebuehr_and_limits_match_serviceratgeber():
    assert _value("rezeptgebuehr") == 7.55
    assert _value("rgb_befreiungsgrenze_alleinstehend") == 1308.39
    assert _value("rgb_befreiungsgrenze_paar") == 2064.12
    assert _value("reha_stufe1_pro_tag") == 11.06


def test_bpgg_paragraph_4_present_and_outdated_amounts_in_par_5():
    rows = {(r["law_key"], r["nr"]): r for r in _jsonl("legal/paragraphs.jsonl")}
    assert "sechs Monate" in rows[("BPGG", "4")]["text"]
    assert "157,30" in rows[("BPGG", "5")]["text"]  # law text = 2020 base amounts -> use values service


def test_eko_known_products():
    meds = _jsonl("eko/medications.jsonl")
    amlo = next(m for m in meds if m["name"].startswith('Amlodipin "Genericon" 5 mg'))
    assert amlo["box"] == "G" and amlo["price_eur"] == 3.65
    assert any(m["box"] == "Y" and m["restriction"] == "RE1" for m in meds)


def test_serviceratgeber_transport_page():
    pages = {r["printed_page"]: r for r in _jsonl("serviceratgeber/pages.jsonl")}
    assert "Transportanweisung" in pages[63]["text"]


def test_form_templates_fillable():
    for form_id in ("fsw_foerderung", "pva_pflegegeld_pal080", "sv_kur_reha", "oegk_fahrtkosten_wien",
                    "oegk_rezeptgebuehr_befreiung"):
        meta = json.loads((ROOT / f"knowledge/forms/templates/{form_id}.fields.json").read_text(encoding="utf-8"))
        assert meta["fillable"] and len(meta["fields"]) >= 10


def test_downloaded_form_has_provenance():
    manifest = json.loads((EX / "MANIFEST.json").read_text(encoding="utf-8"))
    entry = manifest["form_templates_downloaded"]
    assert "knowledge/forms/templates/oegk_rezeptgebuehr_befreiung.pdf" in entry["sources"]
    assert "oegk.at" in entry["notes"]
    meta = json.loads((ROOT / "knowledge/forms/templates/oegk_rezeptgebuehr_befreiung.fields.json").read_text(encoding="utf-8"))
    assert meta["source_url"].startswith("https://www.oegk.at/") and meta["downloaded_at"]
    assert "Antrag auf Befreiung von der Rezeptgebühr" in meta["page_text"][0]
