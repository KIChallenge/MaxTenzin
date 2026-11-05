"""WS-F forms: schema integrity, prefill (Maria -> Anna), session logic, real PDF fill read back with pypdf."""

import io
import json

import pytest
from pypdf import PdfReader

from app.contracts.forms import FieldType
from app.fixtures import ANNA_ANALYSIS
from app.seed.loader import get_person
from app.services.forms import service
from app.services.forms.pdf import DRAFT_STAMP, doctor_only_pdf_fields, field_pages, read_back, render_pdf
from app.services.forms.spec import forms_dir, get_spec, json_schema, load_specs
from app.tests.conftest import auth

MARIA_FOR_ANNA = auth("maria", "anna")
PAL = "pva_pflegegeld_pal080"
MAPPED = ["pva_pflegegeld_pal080"]


def _fields_json(form_id: str) -> dict:
    return json.loads((forms_dir() / "templates" / f"{form_id}.fields.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------------ schema integrity

def test_committed_json_schema_matches_models():
    committed = json.loads((forms_dir().parent / "schema" / "form.schema.json").read_text(encoding="utf-8"))
    assert committed == json_schema(), "run: uv run python -m app.services.forms.spec"


def test_all_yaml_forms_load():
    assert set(MAPPED) <= set(load_specs())


@pytest.mark.parametrize("form_id", MAPPED)
def test_every_pdf_field_exists_in_template(form_id):
    spec = get_spec(form_id)
    names = {f["name"] for f in _fields_json(form_id)["fields"]}
    pdf_names = set(field_pages(form_id))
    for f in spec.fields:
        for target in filter(None, [f.pdf_target, *f.pdf_overflow]):
            assert target in names and target in pdf_names, f"{form_id}: {target!r} not in template"


@pytest.mark.parametrize("form_id", MAPPED)
def test_every_terminal_pdf_field_is_mapped_or_explained(form_id):
    spec = get_spec(form_id)
    mapped = {t for f in spec.fields for t in filter(None, [f.pdf_target, *f.pdf_overflow])}
    blocked = doctor_only_pdf_fields(spec)
    sig = {f["name"] for f in _fields_json(form_id)["fields"] if f["type"] == "signature"}
    missing = set(field_pages(form_id)) - mapped - blocked - set(spec.unmapped_pdf_fields) - sig
    assert not missing, f"{form_id}: unmapped AcroForm fields {sorted(missing)}"


@pytest.mark.parametrize("form_id", MAPPED)
def test_radio_export_values_exist(form_id):
    """Every pdf_options / pdf_on_value is a real appearance state of that field in the template."""
    from pypdf import PdfReader

    from app.services.forms.spec import template_pdf
    states: dict[str, set[str]] = {}
    for page in PdfReader(template_pdf(form_id)).pages:
        for annot in page.get("/Annots") or []:
            a = annot.get_object()
            ap = a.get("/AP", {}).get("/N")
            if ap is None or not hasattr(ap, "keys"):
                continue
            node, parts = a, []
            while node is not None:
                if node.get("/T") is not None:
                    parts.append(str(node["/T"]))
                node = node["/Parent"].get_object() if node.get("/Parent") is not None else None
            states.setdefault(".".join(reversed(parts)), set()).update(str(k) for k in ap)
    for f in get_spec(form_id).fields:
        if f.type == FieldType.choice and f.pdf_target:
            assert set(f.pdf_options.values()) <= states[f.pdf_target], f.id
        if f.type == FieldType.checkbox and f.pdf_target:
            assert f.pdf_on_value in states[f.pdf_target], f.id


# ------------------------------------------------------------------ doctor-only

def test_kur_reha_page2_is_doctor_only_and_never_writable(client):
    spec = get_spec("sv_kur_reha")
    if spec is None:
        pytest.skip("sv_kur_reha not mapped yet")
    blocked = doctor_only_pdf_fields(spec)
    assert {"Antragsrelevante Diagnose", "Aktuelle Vorgeschichte", "Befunde", "Begründung", "kurfähig"} <= blocked
    assert "VSNR_1" not in blocked  # header field shared with page 1 (patient data) stays writable
    for f in spec.fields:
        if f.doctor_only:
            assert f.readonly_reason_de and not f.prefill and not f.required
    sess = client.post("/api/forms/definitions/sv_kur_reha/sessions", headers=MARIA_FOR_ANNA).json()
    doc_fields = [f.id for f in spec.fields if f.doctor_only]
    assert doc_fields
    r = client.patch(f"/api/forms/sessions/{sess['id']}", headers=MARIA_FOR_ANNA,
                     json={"values": {doc_fields[0]: "irgendwas"}})
    assert r.status_code == 422 and "Ärzt" in json.dumps(r.json(), ensure_ascii=False)
    nq = client.get(f"/api/forms/sessions/{sess['id']}/next-questions", headers=MARIA_FOR_ANNA,
                    params={"include_optional": True}).json()
    assert not set(doc_fields) & {q["id"] for q in nq["questions"]}
    # even a tampered session value never reaches a doctor-only AcroForm field
    from app.contracts.forms import FieldValue
    values = {f.id: FieldValue(value="X") for f in spec.fields if f.type in (FieldType.text, FieldType.textarea)}
    filled = read_back(render_pdf(spec, values))
    assert all(not filled.get(name) for name in blocked)


# ------------------------------------------------------------------ prefill

def test_prefill_maria_for_anna():
    spec = get_spec(PAL)
    sess = service.start_session(spec, get_person("anna"), get_person("maria"))
    v = {k: fv.value for k, fv in sess.values.items()}
    assert v["Fam.Name"] == "Berger" and v["Vorname"] == "Anna" and v["Geburtsdatum"] == "14.03.1948"
    assert v["VSNR_1"] == "1234 140348" and v["Geschlecht"] == "weiblich" and v["Personenstand"] == "verwitwet"
    assert (v["Adresse Straße"], v["Hausnummer, Stiege, Tür"], v["PLZ"], v["Ort"]) == ("Musterstraße", "12", "1030", "Wien")
    # §2 Antragstellung durch andere Person = Maria (from actor profile + delegation)
    assert v["Andere Person"] == "bevollmächtigt" and v["Nachweis"] == "liegt bei"
    assert (v["Familienname andere"], v["Vorname andere Person"]) == ("Berger", "Maria")
    assert (v["Adresse Straße 1"], v["PLZ 1"], v["Ort 1"]) == ("Landstraßer Hauptstraße", "1030", "Wien")
    assert v["Email2"] == "maria.berger@example.at"
    # medical content and consents are never prefilled
    for fid in ("Leiden", "Medikamente", "Pflegeberatung", "Antragstellung andere Person", "Demenz"):
        assert v[fid] in (None, False), fid
    # every prefill has a source and is unconfirmed
    for fid, fv in sess.values.items():
        if fv.value not in (None, ""):
            assert fv.source is not None and fv.confirmed is False, fid
    assert sess.values["Andere Person"].source.ref == "delegation:del-anna-maria"


def test_prefill_self_has_no_proxy_section():
    spec = get_spec(PAL)
    sess = service.start_session(spec, get_person("anna"), get_person("anna"))
    assert sess.values["Familienname andere"].value is None and sess.values["Andere Person"].value is None
    assert "Andere Person" not in {q.id for q in service.next_questions(spec, sess).questions}


def test_prefill_from_document_analysis_is_non_medical():
    spec = get_spec(PAL)
    sess = service.start_session(spec, get_person("anna"), get_person("maria"), ANNA_ANALYSIS)
    assert sess.values["Krankenhaus"].value == "ja"
    assert sess.values["Krankenhaus"].source.kind == "document"
    assert sess.values["Unterlagen"].value == "Kopie: Entlassungsbefund.pdf"
    assert sess.values["Leiden"].value is None  # never derived from the document
    ids = [q.id for q in service.next_questions(spec, sess).questions]
    assert ids[:1] == ["Leiden"] and {"KH von", "KH bis", "Spital"} <= set(ids)


# ------------------------------------------------------------------ session logic over HTTP

def test_session_flow_http(client):
    s = client.post(f"/api/forms/definitions/{PAL}/sessions", headers=MARIA_FOR_ANNA).json()
    assert len(s["id"]) == 36 and s["status"] == "draft"
    nq = client.get(f"/api/forms/sessions/{s['id']}/next-questions", headers=MARIA_FOR_ANNA).json()
    assert [q["id"] for q in nq["questions"]] == ["Leiden"] and 0 < nq["progress"] < 1
    opt = client.get(f"/api/forms/sessions/{s['id']}/next-questions", headers=MARIA_FOR_ANNA,
                     params={"include_optional": True}).json()
    assert {"Pflegeberatung", "Krankenhaus", "Hausbesuch"} <= {q["id"] for q in opt["questions"]}

    # conditional questions appear only when relevant
    r = client.patch(f"/api/forms/sessions/{s['id']}", headers=MARIA_FOR_ANNA,
                     json={"values": {"Krankenhaus": True, "Pflegeberatung": "ja"}})
    assert r.status_code == 200 and r.json()["values"]["Krankenhaus"]["value"] == "ja"
    ids = [q["id"] for q in client.get(f"/api/forms/sessions/{s['id']}/next-questions", headers=MARIA_FOR_ANNA).json()["questions"]]
    assert ids == ["Leiden", "KH von", "KH bis", "Spital", "Antragstellung andere Person"]

    # validation -> 422 with German messages
    bad = client.patch(f"/api/forms/sessions/{s['id']}", headers=MARIA_FOR_ANNA,
                       json={"values": {"KH von": "32.13.2026", "Personenstand": "kompliziert", "Gibtsnicht": "x"}})
    assert bad.status_code == 422
    errs = bad.json()["detail"]["fields"]
    assert set(errs) == {"KH von", "Personenstand", "Gibtsnicht"} and "TT.MM.JJJJ" in errs["KH von"]

    ok = client.patch(f"/api/forms/sessions/{s['id']}", headers=MARIA_FOR_ANNA, json={"values": {
        "Leiden": "laut Entlassungsbrief", "KH von": "2026-10-12", "KH bis": "28.10.2026", "Spital": "Klinik Landstraße",
        "Antragstellung andere Person": "ja"}}).json()
    assert ok["values"]["KH von"]["value"] == "12.10.2026" and ok["values"]["KH von"]["confirmed"] is True
    assert ok["status"] == "ready"
    nq = client.get(f"/api/forms/sessions/{s['id']}/next-questions", headers=MARIA_FOR_ANNA).json()
    assert nq["questions"] == [] and nq["progress"] == 1


def test_session_is_scoped_to_subject(client):
    s = client.post(f"/api/forms/definitions/{PAL}/sessions", headers=MARIA_FOR_ANNA).json()
    assert client.get(f"/api/forms/sessions/{s['id']}", headers=auth("stefan")).status_code == 404
    assert client.get("/api/forms/sessions/does-not-exist", headers=MARIA_FOR_ANNA).status_code == 404
    assert client.post("/api/forms/definitions/nope/sessions", headers=MARIA_FOR_ANNA).status_code == 404


def test_definitions_served_from_yaml(client):
    defs = {d["form_id"]: d for d in client.get("/api/forms", headers=auth("anna")).json()}
    assert set(MAPPED) <= set(defs)
    pal = client.get(f"/api/forms/definitions/{PAL}", headers=auth("anna")).json()
    assert pal["sections"][1] == "1 Persönliche Angaben" and len(pal["fields"]) > 90
    assert not any("pdf" in k for k in pal["fields"][0])  # mapping stays internal


def test_start_with_document_id(client):
    from app.core.db import store
    store.put("document_analyses", "doc-test-1", ANNA_ANALYSIS.model_copy(update={"document_id": "doc-test-1"}).model_dump(),
              subject_id="anna")
    s = client.post(f"/api/forms/definitions/{PAL}/sessions", headers=MARIA_FOR_ANNA, params={"document_id": "doc-test-1"})
    assert s.status_code == 200 and s.json()["values"]["Krankenhaus"]["value"] == "ja"
    missing = client.post(f"/api/forms/definitions/{PAL}/sessions", headers=MARIA_FOR_ANNA, params={"document_id": "x"})
    assert missing.status_code == 404


# ------------------------------------------------------------------ render + preview

def test_render_fills_official_pdf(client):
    h = MARIA_FOR_ANNA
    s = client.post(f"/api/forms/definitions/{PAL}/sessions", headers=h).json()
    leiden = ("Mammakarzinom links, Zustand nach brusterhaltender Operation; geplante adjuvante Strahlentherapie; "
              "arterielle Hypertonie")
    client.patch(f"/api/forms/sessions/{s['id']}", headers=h,
                 json={"values": {"Leiden": leiden, "Pflegeberatung": "Ja", "Antragstellung andere Person": True,
                                  "Betreuung durch andere Person": "ja", "mobile Dienste": True,
                                  "Name mobiler Dienst": "Heimhilfe, FSW"}})
    r = client.post(f"/api/forms/sessions/{s['id']}/render", headers=h)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert "ENTWURF" in r.headers["content-disposition"]
    filled = read_back(r.content)
    assert filled["Fam.Name"] == "Berger" and filled["Vorname"] == "Anna" and filled["Geburtsdatum"] == "14.03.1948"
    assert filled["Familienname andere"] == "Berger" and filled["Vorname andere Person"] == "Maria"
    assert filled["Andere Person"] == "/02" and filled["Personenstand"] == "/03" and filled["Pflegeberatung"] == "/02"
    assert filled["Antragstellung andere Person"] == "/01" and filled["mobile Dienste"] == "/ja"
    # long text continues on the second line of the official form, nothing lost
    assert f"{filled['Leiden']} {filled['Leiden2']}" == leiden
    reader = PdfReader(io.BytesIO(r.content))
    assert reader.trailer["/Root"]["/AcroForm"]["/NeedAppearances"] == True  # pypdf BooleanObject
    assert all(DRAFT_STAMP in p.extract_text() for p in reader.pages[:4])
    assert client.get(f"/api/forms/sessions/{s['id']}", headers=h).json()["status"] == "rendered"


def test_render_drops_answers_to_questions_that_no_longer_apply(client):
    h = MARIA_FOR_ANNA
    s = client.post(f"/api/forms/definitions/{PAL}/sessions", headers=h).json()
    client.patch(f"/api/forms/sessions/{s['id']}", headers=h, json={"values": {"Hausbesuch": "ja", "Name weitere Person": "X Y"}})
    client.patch(f"/api/forms/sessions/{s['id']}", headers=h, json={"values": {"Hausbesuch": "nein"}})
    filled = read_back(client.post(f"/api/forms/sessions/{s['id']}/render", headers=h).content)
    assert filled["Hausbesuch"] == "/01" and not filled.get("Name weitere Person")


def test_preview_lists_values_with_sources(client):
    h = MARIA_FOR_ANNA
    s = client.post(f"/api/forms/definitions/{PAL}/sessions", headers=h).json()
    p = client.get(f"/api/forms/sessions/{s['id']}/preview", headers=h).json()
    assert p["missing_required"] == ["Leiden"] and "nichts automatisch" in p["notice_de"]
    by_id = {i["field_id"]: i for i in p["items"]}
    assert by_id["Vorname"]["value"] == "Anna" and by_id["Vorname"]["source"]["label"].startswith("ID Austria")
    assert by_id["Leiden"]["missing"] is True


@pytest.mark.parametrize("form_id", [f for f in MAPPED if f != PAL])
def test_other_forms_prefill_and_render(client, form_id):
    h = MARIA_FOR_ANNA
    s = client.post(f"/api/forms/definitions/{form_id}/sessions", headers=h).json()
    filled = read_back(client.post(f"/api/forms/sessions/{s['id']}/render", headers=h).content)
    assert any(v and "Berger" in v for v in filled.values()), form_id
