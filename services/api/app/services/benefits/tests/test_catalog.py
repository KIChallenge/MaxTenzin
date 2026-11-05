"""Catalog integrity: every benefit/criterion resolves to a real source; schema file is in sync."""

import json

from app.contracts.common import SourceKind
from app.core.knowledge import kpath
from app.services.benefits import catalog
from app.services.benefits.service import EVALUATORS
from app.tests.conftest import auth

REQUIRED = {"pflegegeld", "reha_onko", "fsw_mobile_pflege", "pflegeberatung", "krankentransport", "fahrtkostenzuschuss",
            "rezeptgebuehrenbefreiung", "rezeptgebuehrenobergrenze", "hauskrankenpflege", "unterstuetzungsfonds",
            "vorsorgeuntersuchung", "familienbeihilfe", "kinderbetreuungsgeld", "eltern_kind_pass"}


def test_required_benefits_present_and_evaluated():
    ids = set(catalog.entries())
    assert REQUIRED <= ids
    assert ids == set(EVALUATORS)
    assert next(iter(catalog.entries())) == "pflegegeld"   # smoke test + UI rely on this order


def test_all_sources_resolve_with_in_force_dates():
    for e in catalog.entries().values():
        b = e.benefit
        assert b.legal_basis or b.sources, b.id
        assert b.plain_de and b.name_de and b.area in "ABCDEF"
        for s in b.legal_basis:
            assert s.kind == SourceKind.law and s.in_force and s.ref, (b.id, s)
        for cid, (label, src) in e.criteria.items():
            assert label and src.label, (b.id, cid)
            if src.kind == SourceKind.law:
                assert src.in_force


def test_form_ids_exist():
    for b in catalog.benefits():
        for f in b.form_ids:
            assert kpath("forms", "templates", f"{f}.fields.json").exists(), (b.id, f)


def test_schema_file_in_sync():
    committed = json.loads(kpath("schema", "benefits.schema.json").read_text(encoding="utf-8"))
    assert committed == json.loads(json.dumps(catalog.json_schema()))


def test_catalog_endpoints(client):
    h = auth("anna")
    lst = client.get("/api/benefits", headers=h).json()
    assert len(lst) >= 14 and lst[0]["id"] == "pflegegeld"
    assert all(b["area"] == "F" for b in client.get("/api/benefits", params={"area": "F"}, headers=h).json())
    pg = client.get("/api/benefits/pflegegeld", headers=h).json()
    assert pg["legal_basis"][0]["label"] == "§ 4 BPGG" and pg["legal_basis"][0]["in_force"] == "2015-01-01"
    assert client.get("/api/benefits/gibtsnicht", headers=h).status_code == 404
