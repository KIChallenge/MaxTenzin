"""Rezeptgebühr calculator: values from veraendW 2026 only (1.308,39 / 2.064,12 / +201,88 pro Kind / 7,55 €)."""

from decimal import Decimal

from app.services.benefits.service import rezeptgebuehr_calc
from app.tests.conftest import auth


def test_thresholds():
    assert rezeptgebuehr_calc(1308.39, "alleinstehend").status == "befreit"
    assert rezeptgebuehr_calc(1308.40, "alleinstehend").status == "pruefen_115"
    assert rezeptgebuehr_calc(1400, "alleinstehend", chronic_expenses=True).status == "befreit_115"
    assert rezeptgebuehr_calc(1400, "alleinstehend", chronic_expenses=False).status == "obergrenze"
    assert rezeptgebuehr_calc(1600, "alleinstehend", chronic_expenses=True).status == "obergrenze"
    assert rezeptgebuehr_calc(2064.12, "paar").status == "befreit"
    assert rezeptgebuehr_calc(None, "paar").status == "unknown"
    assert rezeptgebuehr_calc(None, None, receives_ausgleichszulage=True).status == "befreit_ohne_antrag"


def test_children_and_115():
    c = rezeptgebuehr_calc(1700, "alleinstehend", children=2)
    assert c.limit == Decimal("1712.15") and c.status == "befreit"
    assert rezeptgebuehr_calc(1500, "alleinstehend").limit_115 == Decimal("1504.65")   # = Serviceratgeber S. 43


def test_obergrenze():
    c = rezeptgebuehr_calc(2500, "alleinstehend")
    assert c.rego_annual_income == Decimal(30000) and c.rego_cap == Decimal("600.00")
    assert c.rego_packages == 80          # ceil(600 / 7,55)
    low = rezeptgebuehr_calc(900, "alleinstehend")
    assert low.rego_annual_income == Decimal("1308.39") * 12   # Mindestgrenze RRZ § 16 Abs. 4


def test_endpoint(client):
    r = client.get("/api/benefits/rezeptgebuehr/check", headers=auth("anna"),
                   params={"net_income_monthly": 2500, "household": "paar"}).json()
    by = {e["benefit"]["id"]: e for e in r}
    assert by["rezeptgebuehrenbefreiung"]["status"] == "not_applicable"
    assert by["rezeptgebuehrenobergrenze"]["status"] == "likely"
    assert by["rezeptgebuehrenobergrenze"]["amounts"][0]["value"] == 600.0
    bad = client.get("/api/benefits/rezeptgebuehr/check", headers=auth("anna"),
                     params={"net_income_monthly": 1, "household": "wg"})
    assert bad.status_code == 422
