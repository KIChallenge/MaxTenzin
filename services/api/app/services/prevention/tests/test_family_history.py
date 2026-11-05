"""Family history -> 'besonders relevant' programme explanations (use case 3.4). No risk assessment, always 'ask doctor'."""

import re
from datetime import date

from app.contracts.common import SourceKind
from app.seed.loader import get_person
from app.services.prevention.engine import evaluate, knowledge
from app.tests.conftest import auth

AS_OF = date(2026, 11, 5)
NOTE = knowledge()["family_history"]["doctor_note_de"]


def by_id(items):
    return {i.id: i for i in items}


def test_no_family_history_keeps_items_unchanged():
    plain = by_id(evaluate(get_person("stefan"), [], AS_OF)[0])
    same = by_id(evaluate(get_person("stefan"), [], AS_OF, [])[0])
    assert {k: v.model_dump() for k, v in plain.items()} == {k: v.model_dump() for k, v in same.items()}
    assert "darmkrebs" not in plain                          # Stefan is 39: programme starts at 45


def test_stefan_darmkrebs():
    items, rules = evaluate(get_person("stefan"), [], AS_OF, ["Darmkrebs"])
    it = by_id(items)
    dk, vu = it["darmkrebs"], it["vu"]
    assert dk.status == "upcoming" and dk.due_date == "2032-03-22"     # 45th birthday
    for i in (dk, vu):
        assert i.explanation_de.startswith("Besonders relevant wegen Ihrer Familiengeschichte (Darmkrebs)")
        assert i.explanation_de.endswith(NOTE)
        assert any(s.kind == SourceKind.brochure and s.label.endswith("S. 24") for s in i.sources)
    assert "prevention.family_history.darmkrebs.v1" in rules
    assert it["influenza"].explanation_de.startswith("Besonders") is False


def test_brustkrebs_women_only_and_aliases():
    anna = by_id(evaluate(get_person("anna"), [], AS_OF, ["brustkrebs"])[0])
    assert anna["mammografie"].explanation_de.startswith("Besonders relevant")
    assert any("familiär erhöhtes Risiko" in (s.quote or "") for s in anna["mammografie"].sources)
    stefan = by_id(evaluate(get_person("stefan"), [], AS_OF, ["breast cancer"])[0])
    assert "mammografie" not in stefan and stefan["vu"].explanation_de.startswith("Besonders relevant")


def test_multiple_conditions_and_unknown_ignored():
    items, rules = evaluate(get_person("stefan"), [], AS_OF, ["diabetes", "Herz-Kreislauf", "unbekannt"])
    vu = by_id(items)["vu"]
    assert "Diabetes" in vu.explanation_de and "Herz-Kreislauf" in vu.explanation_de
    assert vu.explanation_de.count(NOTE) == 1 and vu.explanation_de.endswith(NOTE)
    assert {"prevention.family_history.diabetes.v1", "prevention.family_history.herz_kreislauf.v1"} <= set(rules)


def test_no_risk_numbers_or_assessment_wording():
    for fh in knowledge()["family_history"]["rules"]:
        text = fh["explanation_de"]
        assert not re.search(r"\d+\s*(%|Prozent)|erhöhtes Risiko haben|Sie sind gefährdet|fehl", text), fh["id"]


def test_overview_endpoint_with_family_history(client):
    r = client.get("/api/prevention/overview", params={"as_of": "2026-11-05", "family_history": ["darmkrebs"]},
                   headers=auth("stefan"))
    assert r.status_code == 200
    items = {i["id"]: i for i in r.json()["items"]}
    assert items["darmkrebs"]["status"] == "upcoming"
    plain = client.get("/api/prevention/overview", params={"as_of": "2026-11-05"}, headers=auth("stefan")).json()
    assert "darmkrebs" not in {i["id"] for i in plain["items"]}
