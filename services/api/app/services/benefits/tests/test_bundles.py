"""Situation bundles: deterministic matching, assembly from the real eligibility/prevention engines, sources, scopes."""

import pytest

from app.services.benefits import bundles
from app.tests.conftest import auth

AS_OF = {"as_of": "2026-11-05"}
MARIA_FOR_ANNA = auth("maria", "anna")
HELP_MOTHER = "Meine Mutter braucht jetzt Hilfe, was muss ich denn da machen?"


def _match(client, headers, **body):
    body.setdefault("facts", {})
    body["facts"] = {**AS_OF, **body["facts"]}
    r = client.post("/api/benefits/bundles/match", headers=headers, json=body)
    assert r.status_code == 200, r.text
    return r.json()


def _items(b):
    """ref_id -> item; benefit/offer items win over an appointment item with the same topic id."""
    out = {}
    for i in b["items"]:
        out.setdefault(i["ref_id"], i)
    return out


@pytest.mark.parametrize(("text", "bundle_id"), [
    (HELP_MOTHER, "pflege_zuhause"),
    ("Meine Mutter ist chronisch krank und kommt allein nicht mehr zurecht", "pflege_zuhause"),
    ("Mein Vater braucht einen Rollator und Pflege", "pflege_zuhause"),
    ("My mother needs help at home", "pflege_zuhause"),
    ("Ich habe einen Entlassungsbrief bekommen – was muss ich jetzt erledigen?", "nach_spital"),
    ("Meine Mutter wurde gestern aus dem Spital entlassen", "nach_spital"),
    ("Ich möchte etwas für meine Gesundheit tun", "gesundheit_foerdern"),
    ("Ich will mit dem Rauchen aufhören und mehr Bewegung", "gesundheit_foerdern"),
    ("I want to get healthy and do more exercise", "gesundheit_foerdern"),
    ("Ich habe ein Kind bekommen", "kind"),
    ("Meine Tochter ist zwei Jahre alt", "kind"),
    ("Ich kann mir die Rezeptgebühr nicht leisten", "finanzielle_unterstuetzung"),
    ("Mein Einkommen reicht nicht, ich brauche finanzielle Hilfe", "finanzielle_unterstuetzung"),
])
def test_text_matching(text, bundle_id):
    m = bundles.match_text(text)
    assert m is not None and m.bundle_id == bundle_id, (text, m)


def test_no_match_returns_none(client):
    assert bundles.match_text("Wie wird das Wetter morgen?") is None
    r = client.post("/api/benefits/bundles/match", headers=auth("stefan"), json={"text": "Wie wird das Wetter?"})
    assert r.status_code == 200 and r.json() is None


def test_bad_requests(client):
    h = auth("stefan")
    assert client.post("/api/benefits/bundles/match", headers=h, json={"situation": "gibtsnicht"}).status_code == 404
    assert client.post("/api/benefits/bundles/match", headers=h, json={}).status_code == 422


def test_knowledge_valid_and_every_item_sourced(client):
    f = bundles.bundles_file()
    assert {b.id for b in f.bundles} == {"pflege_zuhause", "nach_spital", "gesundheit_foerdern", "kind",
                                        "finanzielle_unterstuetzung"}
    cat = client.get("/api/benefits/bundles/catalog", headers=auth("stefan")).json()
    assert [b["id"] for b in cat] == [b.id for b in f.bundles]
    for b in cat:
        assert b["items"] and b["next_step_de"] and len(b["questions_de"]) <= 3
        for i in b["items"]:
            assert i["source"] and i["source"]["label"], (b["id"], i["ref_id"])
            assert i["why_de"]
            if i["kind"] in ("benefit", "offer"):
                assert i["status"] in ("likely", "possible", "needs_info"), (b["id"], i)   # not_applicable left out


def test_validation_rejects_unknown_refs():
    raw = bundles.bundles_file().model_dump(by_alias=True, exclude_none=True)
    raw["bundles"][0]["items"].append({"kind": "benefit", "ref": "gibtsnicht", "why_de": "x"})
    with pytest.raises(ValueError):
        bundles._validate(bundles.BundlesFile.model_validate(raw))
    with pytest.raises(ValueError):
        bundles.ItemSpec(kind="appointment", ref="x", why_de="x")      # appointment needs title + source


def test_maria_for_anna_help_without_document(client):
    b = _match(client, MARIA_FOR_ANNA, text=HELP_MOTHER)
    assert b["id"] == "pflege_zuhause"
    it = _items(b)
    assert next(iter(it)) == "pflegegeld" and it["pflegegeld"]["status"] == "needs_info"
    assert {"pflegeberatung", "fsw_mobile_pflege", "heilbehelfe_hilfsmittel", "ersatzpflege",
            "foerderung_24h_betreuung", "pflegekarenzgeld", "pva_pflegegeld_pal080"} <= set(it)
    assert it["pva-wien-kundenzone"]["kind"] == "office"                  # nearest PVA office for 1030
    assert it["angebot_trittsicher"]["status"] == "likely"               # Anna is 78
    assert b["questions_de"][0].startswith("Wird die Unterstützung voraussichtlich mindestens sechs Monate")
    assert 2 <= len(b["questions_de"]) <= 3


def test_maria_for_anna_help_with_discharge_letter(client):
    b = _match(client, MARIA_FOR_ANNA, text=HELP_MOTHER, document_ids=["doc-anna-entlassung"],
               facts={"aid_needed": True, "aid_type": "Rollator"})
    it = _items(b)
    assert it["fsw_mobile_pflege"]["status"] == "likely"
    assert it["fsw_mobile_pflege"]["source"]["kind"] == "document"
    assert "Im Dokument ausdrücklich empfohlen (Entlassungsbefund.pdf, S. 4)" in it["fsw_mobile_pflege"]["why_de"]
    assert it["pflegegeld"]["source"]["quote"].startswith("Aufgrund")
    assert it["heilbehelfe_hilfsmittel"]["status"] == "possible"
    assert "Wird Hilfe bei der Pflege" not in " ".join(b["questions_de"])   # answered by the letter


def test_document_only_means_nach_spital(client):
    b = _match(client, MARIA_FOR_ANNA, document_ids=["doc-anna-entlassung"])
    assert b["id"] == "nach_spital"
    it = _items(b)
    assert it["reha_onko"]["status"] == "possible" and "sv_kur_reha" in it
    assert next(iter(it)) == "hausarzt_kontrolle"


def test_prevention_needs_scope(client):
    # Anna did not share Vorsorge/health data with Maria -> prevention items are skipped, benefits still shown
    b = _match(client, MARIA_FOR_ANNA, situation="gesundheit_foerdern")
    assert not any(i["kind"] == "prevention" for i in b["items"])
    assert _items(b)["angebot_trittsicher"]["status"] == "likely"
    events = client.get("/api/audit", headers=auth("anna")).json()
    ev = next(e for e in events if e["path"] == "/api/benefits/bundles/match")
    assert "bundles.prevention_skipped_no_scope" in ev["rule_ids"] and "bundles.gesundheit_foerdern.v1" in ev["rule_ids"]


def test_stefan_gesundheit(client):
    b = _match(client, auth("stefan"), text="Ich möchte etwas für meine Gesundheit tun")
    assert b["id"] == "gesundheit_foerdern"
    it = _items(b)
    assert it["vorsorgeuntersuchung"]["status"] == "likely"
    assert it["angebot_bewegt_im_park"]["source"]["kind"] == "external"
    assert {"angebot_gesunder_ruecken", "angebot_gesund_leben_regional", "angebot_richtig_essen",
            "influenza"} <= set(it)
    assert "angebot_trittsicher" not in it and "darmkrebs" not in it and "angebot_therapie_aktiv" not in it
    assert b["questions_de"] and "Familie" in b["questions_de"][0]


def test_stefan_gesundheit_family_history_darmkrebs(client):
    b = _match(client, auth("stefan"), situation="gesundheit_foerdern", facts={"family_history": ["darmkrebs"]})
    it = _items(b)
    dk = it["darmkrebs"]
    assert "Besonders relevant wegen Ihrer Familiengeschichte (Darmkrebs)" in dk["why_de"]
    assert dk["why_de"].endswith("sprechen Sie die Familiengeschichte bei der Vorsorgeuntersuchung an.")
    assert "Besonders relevant" in it["vorsorgeuntersuchung"]["why_de"]
    assert not any("Familie" in q for q in b["questions_de"])


def test_stefan_kind_bundle(client):
    b = _match(client, auth("stefan"), text="Ich habe ein Kind")
    it = _items(b)
    assert b["id"] == "kind" and it["eltern_kind_pass"]["status"] == "possible"
    assert it["familienbeihilfe"]["status"] == "possible"
    assert "kinderimpfprogramm" not in it          # prevention runs for the subject (Stefan), not for Lena


def test_finanzielle_unterstuetzung(client):
    b = _match(client, MARIA_FOR_ANNA, text="Die Rezeptgebühren kann sie sich kaum leisten",
               document_ids=["doc-anna-entlassung"])
    it = _items(b)
    assert b["id"] == "finanzielle_unterstuetzung"
    assert it["sozialhilfe_wien"]["source"]["kind"] == "external"
    assert b["questions_de"][0].startswith("Wie hoch ist das monatliche Nettoeinkommen")
