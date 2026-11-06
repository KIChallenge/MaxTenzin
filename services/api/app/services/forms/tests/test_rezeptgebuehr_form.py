"""ÖGK Antrag auf Befreiung von der Rezeptgebühr: prefill Maria -> Anna, facts -> pension amount, real PDF fill."""

import io

from pypdf import PdfReader

from app.conftest import auth
from app.contracts.forms import FieldType
from app.services.benefits.catalog import benefits
from app.services.forms.pdf import DRAFT_STAMP, read_back
from app.services.forms.spec import get_spec

H = auth("maria", "anna")
RZG = "oegk_rezeptgebuehr_befreiung"


def _start(client) -> dict:
    r = client.post(f"/api/forms/definitions/{RZG}/sessions", headers=H)
    assert r.status_code == 200
    return r.json()


def test_definition_loads_and_is_linked_to_benefit(client):
    spec = get_spec(RZG)
    assert spec is not None and spec.provider == "ÖGK" and spec.form_version == "ÖGK-KSLS/0088-01/V01"
    d = client.get(f"/api/forms/definitions/{RZG}", headers=auth("anna")).json()
    assert d["title_de"].startswith("Antrag auf Befreiung von der Rezeptgebühr")
    benefit = next(b for b in benefits() if b.id == "rezeptgebuehrenbefreiung")
    assert RZG in benefit.form_ids


def test_prefill_maria_for_anna_person_data(client):
    v = _start(client)["values"]
    assert v["name"]["value"] == "Anna Berger"
    assert v["svnr"]["value"] == "1234140348"  # comb field, 10 digits
    assert (v["strasse"]["value"], v["plz"]["value"], v["ort"]["value"]) == ("Musterstraße 12", "1030", "Wien")
    assert v["telefon"]["value"] == "+43 660 1234567"
    assert v["familienstand"]["value"] == "verwitwet"
    assert v["vermerke"]["value"] == "Antrag gestellt von Maria Berger (Tochter, bevollmächtigt)."
    assert v["ort_datum"]["value"].startswith("Wien, ")
    for fid, fv in v.items():
        if fv["value"] not in (None, ""):
            assert fv["source"] is not None and fv["confirmed"] is False, fid


def test_no_checkbox_and_no_declaration_is_prefilled(client):
    spec = get_spec(RZG)
    v = _start(client)["values"]
    for f in spec.fields:
        if f.type == FieldType.checkbox:
            assert v[f.id]["value"] in (None, False), f.id
    for fid in ("packungen", "lebt_allein", "haushalt_1_name", "einkommen_pension_euro"):
        assert v[fid]["value"] is None, fid  # no answers given yet -> nothing invented


def test_known_income_prefills_pension_amount_with_source(client):
    r = client.patch("/api/benefits/facts", headers={**H, "X-Via": "agent", "X-Agent-Tool": "context:save_facts"},
                     json={"facts": {"net_income_monthly": 1150}})
    assert r.status_code == 200
    v = _start(client)["values"]
    amount = v["einkommen_pension_euro"]
    assert amount["value"] == "1.150,00" and amount["confirmed"] is False
    assert amount["source"]["label"].startswith("Angabe von Maria Berger") and "(Lotsi)" in amount["source"]["label"]
    assert amount["source"]["ref"] == "facts:anna#net_income_monthly"
    assert v["einkommen_pension"]["value"] is None  # the person ticks the income type herself


def test_household_rows_follow_lebt_allein(client):
    s = _start(client)
    nq = lambda: [q["id"] for q in client.get(f"/api/forms/sessions/{s['id']}/next-questions", headers=H).json()["questions"]]
    assert {"lebt_allein", "packungen"} <= set(nq()) and "haushalt_1_name" not in nq()
    client.patch(f"/api/forms/sessions/{s['id']}", headers=H, json={"values": {"lebt_allein": "nein",
                                                                               "haushalt_1_name": "Karl Berger"}})
    assert {"haushalt_1_svnr", "haushalt_1_verhaeltnis", "haushalt_1_einkommensart", "haushalt_1_euro"} <= set(nq())
    client.patch(f"/api/forms/sessions/{s['id']}", headers=H, json={"values": {
        "haushalt_1_svnr": "9999 010150", "haushalt_1_verhaeltnis": "Ehemann", "haushalt_1_einkommensart": "Pension",
        "haushalt_1_euro": "900"}})
    row = read_back(client.post(f"/api/forms/sessions/{s['id']}/render", headers=H).content)
    assert (row["Name01_S02"], row["SVNR01_S02"], row["Verw.Verhaeltnis01_S02"], row["EUR04_S02"]) == (
        "Karl Berger", "9999010150", "Ehemann", "900")
    client.patch(f"/api/forms/sessions/{s['id']}", headers=H, json={"values": {"lebt_allein": "ja"}})
    assert not any(i.startswith("haushalt_") for i in nq())  # chained: row follow-ups no longer apply
    filled = read_back(client.post(f"/api/forms/sessions/{s['id']}/render", headers=H).content)
    assert not filled.get("Name01_S02")


def test_render_fills_official_pdf_with_draft_stamp(client):
    client.patch("/api/benefits/facts", headers=H, json={"facts": {"net_income_monthly": 1150}})
    s = _start(client)
    client.patch(f"/api/forms/sessions/{s['id']}", headers=H, json={"values": {
        "einkommen_pension": True, "lebt_allein": "ja", "packungen": "4"}})
    r = client.post(f"/api/forms/sessions/{s['id']}/render", headers=H)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert "ENTWURF" in r.headers["content-disposition"]
    filled = read_back(r.content)
    assert filled["Vor- und Familienname_S1"] == "Anna Berger" and filled["SVNR01_S01"] == "1234140348"
    assert (filled["Straße_S1"], filled["PLZ_S1"], filled["Ort_S1"]) == ("Musterstraße 12", "1030", "Wien")
    assert filled["Familienstand"] == "/verwitwet"
    assert filled["Checkbox10_S1"] == "/Ja" and filled["EUR03_S01"] == "1.150,00"
    assert filled["Packungen01_S01"] == "4" and filled["Vermerke01_S02"].startswith("Antrag gestellt von Maria")
    assert filled["Ort_Datum_S02"].startswith("Wien, ")
    others = [n for n in filled if n.startswith(("Checkbox", "Checkbo15")) and n != "Checkbox10_S1"]
    assert others and all(filled[n] in (None, "/Off") for n in others)
    reader = PdfReader(io.BytesIO(r.content))
    assert all(DRAFT_STAMP in p.extract_text() for p in reader.pages)


def test_render_without_answers_ticks_nothing(client):
    s = _start(client)
    filled = read_back(client.post(f"/api/forms/sessions/{s['id']}/render", headers=H).content)
    ticks = [n for n, val in filled.items() if n.startswith(("Checkbox", "Checkbo15")) and val not in (None, "/Off")]
    assert ticks == []
