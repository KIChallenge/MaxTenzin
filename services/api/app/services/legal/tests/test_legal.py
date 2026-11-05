from app.services.legal import fts, service
from app.tests.conftest import auth


def test_exact_lookup_and_citation(client):
    p = client.get("/api/legal/paragraphs/bpgg/4", headers=auth("anna")).json()
    assert p["citation_de"] == "§ 4 BPGG (in Kraft seit 01.01.2015)"
    assert client.get("/api/legal/paragraphs/BPGG/999", headers=auth("anna")).status_code == 404
    ref = service.source_ref("Satzung_OEGK_2025", "46", "5")
    assert ref.label == "§ 46 Abs. 5 Satzung OEGK 2025" and ref.in_force == "2025-12-20"


def test_fts_ranks_core_law_first(client):
    hits = client.get("/api/legal/search", params={"q": "Pflegegeld Pflegebedarf Stufe"}, headers=auth("anna")).json()
    assert hits and hits[0]["paragraph"]["law_key"] in ("BPGG", "RPGG_2012")
    assert hits[0]["score"] >= hits[-1]["score"]
    assert hits[0]["paragraph"]["citation_de"].endswith(")")


def test_fts_finds_fahrtkosten_rule():
    res = fts.search("Fahrtkosten Strahlentherapie Kilometer", limit=5)
    assert any(r["law_key"] == "Satzung_OEGK_2025" and r["nr"] == "46" for r, _, _ in res)


def test_fts_law_filter_and_prefix():
    res = fts.search("Rezeptgebühr Befreiung", law="rrz_2008", limit=5)
    assert res and all(r["law_key"] == "RRZ_2008" for r, _, _ in res)
    assert fts.search("Kinderbetreuung", law="KBGG", limit=3)       # prefix matches compounds


def test_fts_query_is_sanitised():
    assert fts.match_query('Pflege" OR NEAR(') == '"pflege"* OR "near"*'
    assert fts.search("a b") == []
    assert fts.search('"); DROP TABLE para; --') is not None


def test_index_rebuilt_when_missing():
    path = fts.ensure_index()
    path.unlink()
    fts._ready = None
    assert fts.ensure_index().exists()
