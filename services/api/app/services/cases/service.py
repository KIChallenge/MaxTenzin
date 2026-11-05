"""Mein Fall: turn explicitly documented open tasks + selected benefits into trackable steps (deterministic)."""

from __future__ import annotations

import uuid

from app.contracts.cases import Case, CaseStep, StepStatus
from app.contracts.common import SourceKind, SourceRef
from app.contracts.documents import DocumentAnalysis
from app.core.db import now_iso

# keyword (lowercase) -> (benefit_id, responsible_de). Responsibilities follow the discharge letter task table (§9).
TASK_RULES: list[tuple[str, str | None, str]] = [
    ("pflegegeld", "pflegegeld", "Patientin mit Unterstützung (Vertrauensperson)"),
    ("rehabilitation", "reha_onko", "Behandelnde Ärztin bzw. behandelnder Arzt"),
    ("hauskrankenpflege", "fsw_mobile_pflege", "Entlassungsmanagement und soziale Dienste (FSW)"),
    ("fahrt", "krankentransport", "Patientin, Sozialberatung und Kostenträger"),
    ("rezeptgebühr", "rezeptgebuehrenbefreiung", "Patientin bzw. ÖGK"),
    ("hausärztlich", None, "Patientin bzw. Vertrauensperson"),
    ("bestrahlung", None, "Onkologische Ambulanz und Patientin"),
    ("medikationsplan", None, "Hausärztin und Onkologie"),
]

BENEFIT_TITLES = {
    "pflegegeld": "Pflegegeld beantragen",
    "reha_onko": "Antrag auf onkologische Rehabilitation vorbereiten",
    "fsw_mobile_pflege": "Mobile Pflege beim Fonds Soziales Wien beantragen",
    "krankentransport": "Transport zu Behandlungsterminen klären",
    "fahrtkostenzuschuss": "Fahrtkostenzuschuss prüfen",
    "rezeptgebuehrenbefreiung": "Rezeptgebührenbefreiung beantragen",
    "pflegeberatung": "Kostenlose Pflegeberatung zu Hause anfragen",
}


def _match(task: str) -> tuple[str | None, str]:
    t = task.lower()
    for kw, benefit_id, responsible in TASK_RULES:
        if kw in t:
            return benefit_id, responsible
    return None, "Sie bzw. Ihre Vertrauensperson"


def build_case(subject_id: str, title_de: str, analysis: DocumentAnalysis | None, benefit_ids: list[str]) -> Case:
    steps: list[CaseStep] = []
    covered: set[str] = set()
    if analysis:
        src = SourceRef(kind=SourceKind.document, label=f"{analysis.filename} – offene Aufgaben", ref=analysis.document_id)
        for task in analysis.open_tasks:
            benefit_id, responsible = _match(task)
            if benefit_id:
                covered.add(benefit_id)
            steps.append(CaseStep(id=f"s{len(steps) + 1}", title_de=task, responsible_de=responsible,
                                  benefit_id=benefit_id, source=src))
    for b in benefit_ids:
        if b not in covered:
            steps.append(CaseStep(id=f"s{len(steps) + 1}", title_de=BENEFIT_TITLES.get(b, f"Leistung prüfen: {b}"),
                                  responsible_de="Sie bzw. Ihre Vertrauensperson", benefit_id=b))
    return Case(id=f"case-{uuid.uuid4().hex[:8]}", subject_id=subject_id, title_de=title_de, created_at=now_iso(), steps=steps)


def next_step(case: Case) -> CaseStep | None:
    return next((s for s in case.steps if s.status in (StepStatus.open, StepStatus.in_progress)), None)
