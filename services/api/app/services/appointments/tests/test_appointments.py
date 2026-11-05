from datetime import date, datetime

import pytest

from app.conftest import auth
from app.contracts.appointments import SlotSearch
from app.services.appointments import service

NOW = datetime(2026, 11, 5, 15, 0, tzinfo=service.TZ)   # Thursday afternoon
MA = auth("maria", "anna")                                # Maria acting for Anna (delegation incl. manage_appointments)


@pytest.fixture(autouse=True)
def frozen_now(monkeypatch):
    monkeypatch.setattr(service, "now", lambda: NOW)


def _search(client, headers=MA, **body):
    r = client.post("/api/appointments/slots/search", headers=headers, json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_providers_yaml_real_entries_are_sourced_and_demo_entries_labelled():
    ps = service.providers()
    real = [p for p in ps if not p.demo]
    demo = [p for p in ps if p.demo]
    assert real and demo
    assert all(p.source and p.source.label for p in real)
    assert all("(Demo)" in p.name and p.source is None for p in demo)
    assert {"1030", "1020", "1120", "1220", "1100"} <= {p.zip for p in demo if p.kind == "gp"}
    assert any(p.source.label == "ÖGK Serviceratgeber 2026, S. 94" for p in real)


def test_slots_are_reproducible_and_never_in_the_past():
    day = date(2026, 11, 9)
    assert service.day_slots("demo-gp-1030-muster", day) == service.day_slots("demo-gp-1030-muster", day)
    masked = [t for *_, t in service.day_slots("demo-gp-1030-muster", day)]
    assert any(masked) and not all(masked)            # some slots appear taken, some free
    q = SlotSearch(topic="hausarzt", from_date="2026-11-01", limit=20)
    a, b = service.search(q, "1030", at=NOW), service.search(q, "1030", at=NOW)
    assert [s.id for s in a] == [s.id for s in b]
    assert all(datetime.fromisoformat(s.start) > NOW for s in a)


def test_default_from_date_is_tomorrow(client):
    slots = _search(client, topic="hausarzt", near=False, limit=10)
    assert slots and all(s["start"] >= "2026-11-06" for s in slots)
    assert min(s["start"] for s in slots).startswith("2026-11-06")


def test_daypart_filter(client):
    morning = _search(client, topic="hausarzt", daypart="morning", limit=12)
    afternoon = _search(client, topic="hausarzt", daypart="afternoon", limit=12)
    assert morning and afternoon
    assert all(datetime.fromisoformat(s["start"]).hour < 12 for s in morning)
    assert all(datetime.fromisoformat(s["start"]).hour >= 12 for s in afternoon)


def test_near_ordering_for_anna_1030(client):
    slots = _search(client, topic="hausarzt", daypart="morning", limit=8)   # zip defaults to Anna's 1030
    zips = [s["provider"]["zip"] for s in slots]
    assert zips[0] == "1030" and slots[0]["distance_hint_de"] == "im selben Bezirk (1030)"
    first_other = next(i for i, z in enumerate(zips) if z != "1030")
    assert all(z == "1030" for z in zips[:first_other])
    assert "Nachbarbezirk" in slots[first_other]["distance_hint_de"]
    assert all(s["demo"] for s in slots)


def test_filters_kind_specialty_accessible(client):
    acc = _search(client, topic="hausarzt", accessible_only=True, limit=20)
    assert acc and all(s["provider"]["accessible"] for s in acc)
    gyn = _search(client, specialty="gynäkologie", limit=5)
    assert gyn and all(s["provider"]["specialty"] == "Gynäkologie" for s in gyn)
    counsel = _search(client, topic="pflegeberatung", kind="counselling", limit=4)
    assert counsel and counsel[0]["provider"]["zip"] == "1030" and not counsel[0]["provider"]["demo"]
    assert _search(client, topic="vu", limit=3)        # alias -> vorsorgeuntersuchung


def test_providers_endpoint_sorted_by_proximity(client):
    ps = client.get("/api/appointments/providers", params={"topic": "pflegegeld"}, headers=MA).json()
    assert ps[0]["zip"] == "1030" and ps[0]["source"]["label"]


def test_booking_double_booking_and_cancel(client):
    slot = _search(client, topic="hausarzt", daypart="morning", limit=1)[0]
    body = {"slot_id": slot["id"], "purpose_de": "Kontrolle nach dem Spitalsaufenthalt"}
    r = client.post("/api/appointments", headers=MA, json=body)
    assert r.status_code == 200, r.text
    appt = r.json()
    assert appt["subject_id"] == "anna" and appt["booked_by"] == "maria" and appt["status"] == "booked"
    assert appt["bring_documents_de"][0] == "e-card"
    assert any("Vollmacht" in d for d in appt["bring_documents_de"])
    assert appt["notice_de"].startswith("Demo-Termin")
    # booked slot disappears and cannot be booked twice
    assert slot["id"] not in [s["id"] for s in _search(client, topic="hausarzt", daypart="morning", limit=20)]
    assert client.post("/api/appointments", headers=MA, json=body).status_code == 409
    assert any(a["id"] == appt["id"] for a in client.get("/api/appointments", headers=MA).json())
    # cancel -> slot free again
    c = client.post(f"/api/appointments/{appt['id']}/cancel", headers=MA).json()
    assert c["status"] == "cancelled"
    assert client.post("/api/appointments", headers=MA, json=body).status_code == 200


def test_masked_past_and_unknown_slots_rejected(client):
    day = date(2026, 11, 9)
    masked = next(s for s, _, t in service.day_slots("demo-gp-1030-muster", day) if t)
    for sid in (service.slot_id("demo-gp-1030-muster", masked),
                "demo-gp-1030-muster@2026-11-02T08:00+01:00",           # in the past
                "demo-gp-1030-muster@2026-11-09T03:00+01:00"):          # outside opening hours
        r = client.post("/api/appointments", headers=MA, json={"slot_id": sid, "purpose_de": "Kontrolle"})
        assert r.status_code == 409, sid
    r = client.post("/api/appointments", headers=MA, json={"slot_id": "nope@2026-11-09T08:00", "purpose_de": "x"})
    assert r.status_code == 404


def test_subject_isolation(client):
    slot = _search(client, topic="hausarzt", limit=1)[0]
    appt = client.post("/api/appointments", headers=MA, json={"slot_id": slot["id"], "purpose_de": "Kontrolle"}).json()
    stefan = auth("stefan")
    assert client.get(f"/api/appointments/{appt['id']}/ics", headers=stefan).status_code == 404
    assert client.post(f"/api/appointments/{appt['id']}/cancel", headers=stefan).status_code == 404
    assert all(a["id"] != appt["id"] for a in client.get("/api/appointments", headers=stefan).json())
    # Anna herself sees it
    assert any(a["id"] == appt["id"] for a in client.get("/api/appointments", headers=auth("anna")).json())


def test_ics_is_valid_calendar(client):
    slot = _search(client, topic="influenza", kind="vaccination", limit=1)[0]
    appt = client.post("/api/appointments", headers=auth("anna"),
                       json={"slot_id": slot["id"], "purpose_de": "Grippeimpfung, Termin; bitte, danke"}).json()
    assert any("Impfpass" in d for d in appt["bring_documents_de"])
    assert not any("Vollmacht" in d for d in appt["bring_documents_de"])   # Anna books for herself
    r = client.get(appt["ics_url"], headers=auth("anna"))
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/calendar")
    raw = r.text
    assert raw.startswith("BEGIN:VCALENDAR\r\n") and raw.endswith("END:VCALENDAR\r\n")
    assert all(len(line.encode()) <= 75 for line in raw.split("\r\n"))
    unfolded = raw.replace("\r\n ", "")
    start = datetime.fromisoformat(slot["start"]).strftime("%Y%m%dT%H%M%S")
    assert f"DTSTART;TZID=Europe/Vienna:{start}" in unfolded
    assert "DTEND;TZID=Europe/Vienna:" in unfolded and "BEGIN:VTIMEZONE" in unfolded
    assert "SUMMARY:Termin: Impfstelle" in unfolded
    assert "LOCATION:" in unfolded and "UID:" in unfolded and "DTSTAMP:" in unfolded
    assert "Mitbringen: e-card\\, Impfpass" in unfolded
    assert "Termin\\; bitte\\, danke" in unfolded
    assert "Demo-Termin" in unfolded and "STATUS:CONFIRMED" in unfolded


def test_case_step_link_sets_in_progress(client):
    case = client.post("/api/cases", headers=MA, json={"subject_id": "anna", "title_de": "Nach dem Spital",
                                                       "document_id": "doc-anna-entlassung"}).json()
    step = next(s for s in case["steps"] if "hausärztlichen Kontrolle" in s["title_de"])
    slot = _search(client, topic="hausarzt_kontrolle", daypart="morning", limit=1)[0]
    r = client.post("/api/appointments", headers=MA, json={
        "slot_id": slot["id"], "purpose_de": "Kontrolltermin nach Spitalsentlassung",
        "case_id": case["id"], "step_id": step["id"]})
    assert r.status_code == 200, r.text
    appt = r.json()
    assert appt["case_id"] == case["id"] and appt["step_id"] == step["id"]
    assert any("Entlassungsbrief" in d for d in appt["bring_documents_de"])
    updated = client.get(f"/api/cases/{case['id']}", headers=MA).json()
    assert next(s for s in updated["steps"] if s["id"] == step["id"])["status"] == "in_progress"
    # unknown step -> 404, nothing booked
    slot2 = _search(client, topic="hausarzt", limit=1)[0]
    bad = client.post("/api/appointments", headers=MA, json={"slot_id": slot2["id"], "purpose_de": "x",
                                                             "case_id": case["id"], "step_id": "nope"})
    assert bad.status_code == 404
    assert slot2["id"] in [s["id"] for s in _search(client, topic="hausarzt", limit=1)]


def test_scopes_maria_for_anna_and_stefan_denied(client):
    assert client.post("/api/appointments/slots/search", headers=MA, json={"topic": "hausarzt"}).status_code == 200
    denied = auth("stefan", "anna")
    assert client.post("/api/appointments/slots/search", headers=denied, json={}).status_code == 403
    assert client.post("/api/appointments", headers=denied, json={"slot_id": "x@y", "purpose_de": "x"}).status_code == 403
    assert client.get("/api/appointments", headers=denied).status_code == 403


def test_revoked_scope_blocks_booking(client):
    # Anna narrows Maria's delegation: without manage_appointments, Maria (and Lotsi acting for her) gets 403
    r = client.put("/api/identity/delegations/del-anna-maria/scopes",
                   json=["read_documents", "manage_case"], headers=auth("anna"))
    assert r.status_code == 200
    assert client.post("/api/appointments/slots/search", headers=MA, json={}).status_code == 403
