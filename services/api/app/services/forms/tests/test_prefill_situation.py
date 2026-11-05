"""Prefill rule kind `situation.<key>` + alternatives ("a|b"): situation first, document as fallback, never mixed."""

from datetime import date

from app.contracts.common import SourceKind, SourceRef
from app.contracts.documents import DocumentFact
from app.core.db import store
from app.fixtures import ANNA_ANALYSIS
from app.seed.loader import delegations_for, get_person, reset_delegations
from app.services.forms.prefill import prefill
from app.services.forms.spec import get_spec

ANNA, MARIA = get_person("anna"), get_person("maria")
DELEG = next(d for d in delegations_for("anna") if d.grantee_id == "maria")
ANALYSIS = ANNA_ANALYSIS.model_copy(update={"facts": [
    DocumentFact(key="discharge_date", value="29.10.2026", quote="Entlassungsdatum 29.10.2026", page=1)]})
SRC = SourceRef(kind=SourceKind.external, label="Angabe von Maria Berger, 05.11.2026", ref="situation:person")


def _put(ep_id: str, **kw) -> None:
    store.put("episodes", ep_id, {"id": ep_id, "subject_id": "anna", "title_de": "x", "status": "confirmed",
                                  "created_by": "maria", "source": SRC.model_dump(), "start": None, "end": None,
                                  "institution": None, **kw}, subject_id="anna")


def _clear() -> None:
    for d in store.list("episodes", subject_id="anna"):
        store.delete("episodes", d["id"])


def test_document_fallback_without_situation():
    reset_delegations()
    _clear()
    v = prefill(get_spec("pva_pflegegeld_pal080"), ANNA, MARIA, DELEG, ANALYSIS, today=date(2026, 11, 5))
    assert v["KH bis"].value == "29.10.2026" and v["KH bis"].source.kind == SourceKind.document
    assert v["Krankenhaus"].value == "ja"


def test_situation_wins_and_known_empty_stops_fallback():
    reset_delegations()
    _clear()
    try:
        # an active rehab stay without end date is the most recent stay: KH bis stays empty (no mixing with the letter)
        _put("ep-t-reha", type="rehab_inpatient", start="2026-11-01", institution="Reha-Zentrum (Demo)")
        _put("ep-t-hosp", type="hospital", start="2026-10-20", end="2026-10-29")
        v = prefill(get_spec("pva_pflegegeld_pal080"), ANNA, MARIA, DELEG, ANALYSIS, today=date(2026, 11, 5))
        assert v["KH von"].value == "01.11.2026" and v["KH bis"].value is None
        assert v["Spital"].value == "Reha-Zentrum (Demo)" and v["Spital"].source.label.startswith("Angabe von")
        assert v["KH von 2"].value == "20.10.2026" and v["KH bis 2"].value == "29.10.2026"
        # Stefan (no delegation from Anna) never gets Anna's situation
        stefan = get_person("stefan")
        v2 = prefill(get_spec("pva_pflegegeld_pal080"), ANNA, stefan, None, None, today=date(2026, 11, 5))
        assert v2["KH von"].value is None
    finally:
        _clear()


def test_kur_reha_previous_stays_from_ended_rehab():
    reset_delegations()
    _clear()
    try:
        _put("ep-t-kur", type="cure", start="2024-03-01", end="2024-03-21", institution="Kurhaus (Demo)")
        v = prefill(get_spec("sv_kur_reha"), ANNA, MARIA, DELEG, None, today=date(2026, 11, 5))
        assert v["Aufenthalt innerhalb von  Jahren"].value == "ja"
        assert v["Wann1"].value == "01.03.2024 – 21.03.2024" and v["Wo1"].value == "Kurhaus (Demo)"
    finally:
        _clear()
