"""Lebenslage: suggestions from the discharge letter need consent; confirmed episodes drive facts, reminders,
form prefill and Mein-Fall steps. Scopes: manage_situation (+ read_documents for suggestions), subject isolation."""

from datetime import date, timedelta

import pytest

from app.conftest import auth
from app.contracts.situation import EpisodeStatus
from app.core.db import store
from app.services.situation import service as svc

MARIA_ANNA = auth("maria", "anna")
DOC = "doc-anna-entlassung"
TODAY = date.today()


def _wipe(subject_id: str) -> None:
    for coll in (svc.COLL, "cases", "form_sessions"):
        for d in store.list(coll, subject_id=subject_id):
            store.delete(coll, d["id"])


@pytest.fixture(autouse=True)
def clean():
    for s in ("anna", "stefan", "lena", "maria"):
        _wipe(s)
    yield
    for s in ("anna", "stefan", "lena", "maria"):
        _wipe(s)


def _by_type(eps: list[dict]) -> dict[str, dict]:
    return {e["type"]: e for e in eps}


def test_suggestions_have_quotes_and_no_effect(client):
    eps = client.post(f"/api/situation/suggestions/from-document/{DOC}", headers=MARIA_ANNA).json()
    t = _by_type(eps)
    assert set(t) == {"hospital", "home_care", "therapy", "rehab_inpatient"}
    assert all(e["status"] == "suggested" for e in eps)
    assert all(e["source"]["kind"] == "document" and e["source"]["quote"] for e in eps)
    h = t["hospital"]
    assert h["end"] == "2026-10-29" and h["start"] is None
    assert h["institution"] == "Abteilung für Innere Medizin und Onkologie"
    assert h["source"]["quote"] == "Entlassungsdatum 29.10.2026" and h["source"]["label"].endswith("S. 1")
    assert t["home_care"]["start"] == "2026-10-29" and "Hauskrankenpflege" in t["home_care"]["source"]["quote"]
    assert t["therapy"]["subtype"] == "strahlentherapie" and t["therapy"]["title_de"] == "Ambulante Strahlentherapie"
    assert "Strahlentherapie" in t["therapy"]["source"]["quote"]
    assert t["rehab_inpatient"]["start"] is None and t["rehab_inpatient"]["source"]["label"].endswith("S. 5")

    ov = client.get("/api/situation", headers=MARIA_ANNA).json()
    assert len(ov["suggestions"]) == 4 and not ov["current"] and not ov["upcoming"] and not ov["past"]
    assert ov["effects"] == [] and ov["facts"] == {}
    assert "warten auf Ihre Bestätigung" in ov["summary_de"]
    assert svc.situation_facts("anna") == {} and svc.situation_reminders("anna") == []
    s = client.post("/api/forms/definitions/pva_pflegegeld_pal080/sessions", headers=MARIA_ANNA).json()
    assert s["values"]["KH bis"]["value"] is None and s["values"]["Spital"]["value"] is None


def test_suggest_is_idempotent_and_keeps_decisions(client):
    first = _by_type(client.post(f"/api/situation/suggestions/from-document/{DOC}", headers=MARIA_ANNA).json())
    client.post(f"/api/situation/suggestions/{first['rehab_inpatient']['id']}/reject", headers=MARIA_ANNA)
    again = client.post(f"/api/situation/suggestions/from-document/{DOC}", headers=MARIA_ANNA).json()
    assert len(again) == 4 and len(store.list(svc.COLL, subject_id="anna")) == 4
    assert _by_type(again)["rehab_inpatient"]["status"] == "rejected"
    ov = client.get("/api/situation", headers=MARIA_ANNA).json()
    assert len(ov["suggestions"]) == 3


def test_confirm_drives_facts_reminders_prefill_and_case_steps(client):
    case = client.post("/api/cases", json={"subject_id": "anna", "title_de": "Nach dem Spital", "document_id": DOC},
                       headers=auth("maria", "anna")).json()
    eps = client.post(f"/api/situation/suggestions/from-document/{DOC}", headers=MARIA_ANNA).json()
    for e in eps:
        r = client.post(f"/api/situation/suggestions/{e['id']}/confirm", headers=MARIA_ANNA)
        assert r.status_code == 200 and r.json()["confirmed_by"] == "maria"
    ov = client.get("/api/situation", headers=MARIA_ANNA, params={"as_of": "2026-11-05"}).json()
    assert ov["summary_de"] == "Zu Hause mit Unterstützung · laufende Strahlentherapie · Reha geplant"
    assert [e["type"] for e in ov["past"]] == ["hospital"] and not ov["suggestions"]
    assert ov["facts"] == {"living_at_home_with_support": True, "treatment_type": "strahlentherapie"}

    kinds = {}
    for eff in ov["effects"]:
        kinds.setdefault(eff["kind"], []).append(eff)
        assert eff["source"], eff
    melde = next(e for e in kinds["reminder"] if e["key"] == "meldepflicht:hospital")
    assert melde["due_date"] == "2026-11-26" and "4 Wochen" in melde["title_de"]
    assert melde["source"]["label"].startswith("PAL 080")
    kontrolle = next(e for e in kinds["reminder"] if e["key"] == "appointment:hausarzt_kontrolle")
    assert kontrolle["value"] == "hausarzt_kontrolle" and kontrolle["source"]["quote"] == "Zeitnahe Kontrolle nach der Entlassung."
    prefill = {e["key"]: e["value"] for e in kinds["prefill"]}
    assert prefill["pva_pflegegeld_pal080:KH bis"] == "29.10.2026"
    assert prefill["pva_pflegegeld_pal080:Spital"] == "Abteilung für Innere Medizin und Onkologie"
    assert prefill["oegk_fahrtkosten_wien:Art der Behandlung"] == "Ambulante Strahlentherapie"
    assert {e["title_de"] for e in kinds["case_step"]} >= {"Spitalsaufenthalt an die PVA melden (bis 26.11.2026)",
                                                           "Reha antreten",
                                                           "Nach der Reha: Pflegebedarf neu einschätzen lassen"}

    # Mein Fall got the steps (once), with sources
    c = client.get(f"/api/cases/{case['id']}", headers=MARIA_ANNA).json()
    sit = [s for s in c["steps"] if s["id"].startswith("sit-")]
    titles = [s["title_de"] for s in sit]
    assert "Spitalsaufenthalt an die PVA melden (bis 26.11.2026)" in titles and "Reha antreten" in titles
    assert all(s["source"] for s in sit)
    client.post(f"/api/situation/suggestions/{eps[0]['id']}/confirm", headers=MARIA_ANNA)
    c2 = client.get(f"/api/cases/{case['id']}", headers=MARIA_ANNA).json()
    assert len(c2["steps"]) == len(c["steps"])

    # PAL 080 § 5 prefilled from the episode (Maria acting for Anna), source = the episode's document quote
    s = client.post("/api/forms/definitions/pva_pflegegeld_pal080/sessions", headers=MARIA_ANNA).json()
    v = s["values"]
    assert v["Krankenhaus"]["value"] == "ja"
    assert v["KH bis"]["value"] == "29.10.2026" and v["KH bis"]["source"]["quote"] == "Entlassungsdatum 29.10.2026"
    assert v["Spital"]["value"] == "Abteilung für Innere Medizin und Onkologie" and v["Spital"]["confirmed"] is False
    assert v["Spital"]["source"]["quote"].startswith("Abteilung für Innere Medizin und Onkologie")
    assert v["KH von"]["value"] is None   # start unknown: asked, never guessed

    assert svc.situation_facts("anna") == ov["facts"]
    assert {r.key for r in svc.situation_reminders("anna", date(2026, 11, 5))} == {
        "meldepflicht:hospital", "appointment:hausarzt_kontrolle", "meldepflicht:rehab_inpatient"}


def test_pflegegeld_ruht_hint_cites_bpgg_12_for_current_stay(client):
    store.put("form_sessions", "fs-test-pg", {"id": "fs-test-pg", "form_id": "pva_pflegegeld_pal080",
                                             "subject_id": "anna"}, subject_id="anna")
    start = (TODAY + timedelta(days=4)).isoformat()
    r = client.post("/api/situation/episodes", json={"type": "rehab_inpatient", "start": start,
                                                     "institution": "Reha-Zentrum (Demo)"}, headers=MARIA_ANNA)
    assert r.status_code == 200 and r.json()["status"] == "planned"
    assert r.json()["source"]["label"].startswith("Angabe von Maria Berger, ")
    ov = client.get("/api/situation", headers=MARIA_ANNA).json()
    hint = next(e for e in ov["effects"] if e["key"] == "pflegegeld_ruht")
    assert hint["source"]["label"] == "§ 12 Abs. 1 BPGG" and hint["source"]["in_force"]
    melde = next(e for e in ov["effects"] if e["key"] == "meldepflicht:rehab_inpatient")
    assert melde["due_date"] == (TODAY + timedelta(days=32)).isoformat()
    assert ov["summary_de"] == "Reha geplant"


def test_scopes_and_subject_isolation(client):
    eps = client.post(f"/api/situation/suggestions/from-document/{DOC}", headers=MARIA_ANNA).json()
    # Stefan cannot address Anna (no delegation) and never sees her episodes through his own subject
    assert client.get("/api/situation", headers=auth("stefan", "anna")).status_code == 403
    for path in (f"/api/situation/suggestions/{eps[0]['id']}/confirm", f"/api/situation/suggestions/{eps[0]['id']}/reject"):
        assert client.post(path, headers=auth("stefan")).status_code == 404
    assert client.patch(f"/api/situation/episodes/{eps[0]['id']}", json={"end": "2026-10-30"},
                        headers=auth("stefan")).status_code == 404
    assert client.delete(f"/api/situation/episodes/{eps[0]['id']}", headers=auth("stefan")).status_code == 404
    assert client.get("/api/situation", headers=auth("stefan")).json()["suggestions"] == []
    # Maria without manage_situation -> 403
    r = client.put("/api/identity/delegations/del-anna-maria/scopes", headers=auth("anna"),
                   json=["read_documents", "prepare_applications", "manage_case"])
    assert r.status_code == 200, r.text
    assert client.get("/api/situation", headers=MARIA_ANNA).status_code == 403
    assert client.post(f"/api/situation/suggestions/from-document/{DOC}", headers=MARIA_ANNA).status_code == 403


def test_suggestions_need_read_documents(client):
    r = client.put("/api/identity/delegations/del-anna-maria/scopes", headers=auth("anna"),
                   json=["manage_situation", "manage_case"])
    assert r.status_code == 200
    r = client.post(f"/api/situation/suggestions/from-document/{DOC}", headers=MARIA_ANNA)
    assert r.status_code == 403 and "read_documents" in r.json()["detail"]


def test_prefill_needs_manage_situation(client):
    eps = client.post(f"/api/situation/suggestions/from-document/{DOC}", headers=MARIA_ANNA).json()
    hosp = _by_type(eps)["hospital"]
    client.post(f"/api/situation/suggestions/{hosp['id']}/confirm", headers=MARIA_ANNA)
    client.put("/api/identity/delegations/del-anna-maria/scopes", headers=auth("anna"),
               json=["read_documents", "prepare_applications", "manage_case"])
    s = client.post("/api/forms/definitions/pva_pflegegeld_pal080/sessions", headers=MARIA_ANNA).json()
    assert s["values"]["KH bis"]["value"] is None


def test_status_transitions_with_injected_today():
    raw = {"status": "confirmed", "start": "2026-11-10", "end": "2026-12-01"}
    assert svc.compute_status(raw, date(2026, 11, 5)) == EpisodeStatus.planned
    assert svc.compute_status(raw, date(2026, 11, 10)) == EpisodeStatus.active
    assert svc.compute_status(raw, date(2026, 12, 1)) == EpisodeStatus.active
    assert svc.compute_status(raw, date(2026, 12, 2)) == EpisodeStatus.ended
    assert svc.compute_status({"status": "confirmed"}, date(2026, 11, 5)) == EpisodeStatus.active
    assert svc.compute_status({"status": "confirmed", "manual_status": "planned"}, date(2026, 11, 5)) == "planned"
    assert svc.compute_status({"status": "confirmed", "manual_status": "ended", "start": "2026-11-01"},
                              date(2026, 11, 5)) == EpisodeStatus.ended
    for st in ("suggested", "rejected"):
        assert svc.compute_status({"status": st, "start": "2020-01-01", "end": "2020-02-01"}, date(2026, 11, 5)) == st


def test_overview_as_of_moves_episode_between_groups(client):
    r = client.post("/api/situation/episodes", json={"type": "hospital", "start": "2026-12-01", "end": "2026-12-05",
                                                     "institution": "Klinik Ottakring (Demo)"}, headers=auth("stefan"))
    assert r.status_code == 200
    groups = {d: client.get("/api/situation", headers=auth("stefan"), params={"as_of": d}).json()
              for d in ("2026-11-05", "2026-12-03", "2026-12-20")}
    assert len(groups["2026-11-05"]["upcoming"]) == 1
    assert len(groups["2026-12-03"]["current"]) == 1 and groups["2026-12-03"]["facts"] == {"in_hospital": True}
    assert groups["2026-12-03"]["summary_de"] == "Im Krankenhaus"
    assert len(groups["2026-12-20"]["past"]) == 1
    # no Pflegegeld involved -> no Meldepflicht reminder for Stefan
    assert not [e for e in groups["2026-12-03"]["effects"] if e["key"] == "meldepflicht:hospital"]


def test_create_patch_delete_validation(client):
    h = auth("stefan")
    assert client.post("/api/situation/episodes", json={"type": "home_care", "subtype": "dialyse"},
                       headers=h).status_code == 422
    assert client.post("/api/situation/episodes", json={"type": "sick_leave", "start": "05.11.2026"},
                       headers=h).status_code == 422
    assert client.post("/api/situation/episodes", json={"type": "sick_leave", "start": "2026-11-05",
                                                        "end": "2026-11-01"}, headers=h).status_code == 422
    e = client.post("/api/situation/episodes", json={"type": "therapy", "subtype": "dialyse"}, headers=h).json()
    assert e["status"] == "active" and e["title_de"] == "Dialyse"
    assert client.get("/api/situation", headers=h).json()["facts"] == {"treatment_type": "dialyse"}
    ended = client.patch(f"/api/situation/episodes/{e['id']}", json={"status": "ended"}, headers=h).json()
    assert ended["status"] == "ended" and ended["end"] == TODAY.isoformat()
    assert client.patch(f"/api/situation/episodes/{e['id']}", json={"status": "rejected"}, headers=h).status_code == 422
    assert client.delete(f"/api/situation/episodes/{e['id']}", headers=h).json()["deleted"] is True
    assert client.get("/api/situation", headers=h).json()["past"] == []


def test_page_text_gives_ambulant_quote_and_end_estimate():
    from app.fixtures import ANNA_ANALYSIS

    pages = [("Die Bestrahlung erfolgt ambulant an mehreren Tagen pro Woche. Der Abschluss der geplanten Therapie\n"
             "ist für Mitte November 2026 vorgesehen. \nNebendiagnosen:")]
    out = {s["rule"]: s for s in svc.suggest_from_analysis(ANNA_ANALYSIS, pages)}
    t = out["therapy"]
    assert t["end_estimate_de"] == "Mitte November 2026"
    assert t["source"].quote.startswith("Die Bestrahlung erfolgt ambulant") and t["source"].label.endswith("S. 1")
    assert "Mitte November 2026" in t["source"].quote


def test_imaging_report_suggests_nothing():
    from app.contracts.documents import DocumentType
    from app.fixtures import ANNA_ANALYSIS

    assert svc.suggest_from_analysis(ANNA_ANALYSIS.model_copy(update={"doc_type": DocumentType.imaging_report})) == []
