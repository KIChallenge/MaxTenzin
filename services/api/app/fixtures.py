"""Contract-valid fixture data for stub endpoints (Phase 0). Workstreams replace stubs with real logic.

Facts here mirror the fictional Entlassungsbefund (Anna Berger) and e-Impfpass (Stefan Testpatient).
"""

from app.contracts.benefits import Benefit, CriterionResult, EligibilityResult, EligibilityStatus
from app.contracts.cases import Case, CaseStep
from app.contracts.common import SourceKind, SourceRef
from app.contracts.documents import DocumentAnalysis, DocumentType, ExtractedPerson, Recommendation
from app.contracts.misc import Notification, Office
from app.contracts.prevention import PreventionItem, PreventionOverview, PreventionStatus, VaccinationEntry

DOC = "Entlassungsbefund.pdf"


def _q(quote: str, page: int) -> SourceRef:
    return SourceRef(kind=SourceKind.document, label=f"{DOC}, S. {page}", ref=f"page:{page}", quote=quote)


ANNA_ANALYSIS = DocumentAnalysis(
    document_id="doc-anna-entlassung",
    filename=DOC,
    doc_type=DocumentType.discharge_letter,
    pages=7,
    person=ExtractedPerson(first_name="Anna", last_name="Berger", birth_date="1948-03-14",
                           address="Musterstraße 12, 1030 Wien", insurer="ÖGK",
                           living_situation="Lebt allein in einer Mietwohnung mit Lift"),
    recommendations=[
        Recommendation(id="r1", page=5, category="rehabilitation", related_benefit_ids=["reha_onko"],
                       text_de="Im Entlassungsbrief wird die Prüfung einer stationären onkologischen Rehabilitation nach Abschluss der Strahlentherapie empfohlen.",
                       quote="Prüfung einer stationären onkologischen Rehabilitation nach Abschluss der geplanten Strahlentherapie."),
        Recommendation(id="r2", page=6, category="care", related_benefit_ids=["pflegegeld"],
                       text_de="Laut Entlassungsbrief soll geprüft werden, ob die Voraussetzungen für Pflegegeld erfüllt sind.",
                       quote="Aufgrund des voraussichtlich längerfristigen Unterstützungsbedarfs soll geprüft werden, ob die Voraussetzungen für Pflegegeld erfüllt sind."),
        Recommendation(id="r3", page=4, category="care", related_benefit_ids=["fsw_mobile_pflege"],
                       text_de="Im Entlassungsbrief wird mobile Hauskrankenpflege empfohlen.",
                       quote="Mobile Hauskrankenpflege zur Unterstützung bei pflegerischen Aufgaben und zur Beobachtung des Allgemeinzustands."),
        Recommendation(id="r4", page=6, category="transport", related_benefit_ids=["krankentransport", "fahrtkostenzuschuss"],
                       text_de="Laut Entlassungsbrief soll geklärt werden, ob eine Transportleistung zu den Bestrahlungsterminen in Betracht kommt.",
                       quote="Prüfung, ob aufgrund des Gesundheitszustands und der geltenden Voraussetzungen eine medizinisch begründete Transportleistung zulasten des zuständigen Kostenträgers in Betracht kommt."),
        Recommendation(id="r5", page=6, category="costs", related_benefit_ids=["rezeptgebuehrenbefreiung"],
                       text_de="Laut Entlassungsbrief soll über die Rezeptgebührenbefreiung informiert werden.",
                       quote="Bei entsprechender finanzieller Situation Information über die Voraussetzungen einer Rezeptgebührenbefreiung."),
    ],
    open_tasks=[
        "Termin zur hausärztlichen Kontrolle vereinbaren",
        "Weitere Bestrahlungstermine koordinieren",
        "Aktuellen Medikationsplan abstimmen",
        "Mobile Hauskrankenpflege organisieren",
        "Rehabilitationsantrag vorbereiten",
        "Pflegegeldanspruch prüfen",
        "Fahrtmöglichkeiten zu Behandlungsterminen klären",
        "Rezeptgebührenbefreiung prüfen",
    ],
    extraction_mode="golden",
)

BPGG4 = SourceRef(kind=SourceKind.law, label="§ 4 BPGG", ref="BPGG=PARA=4=12=2015-01-13=2015-01-01", in_force="2015-01-01")
VAL_PG1 = SourceRef(kind=SourceKind.value, label="veraendW Tab. 54 (2026)", ref="pflegegeld_stufe_1")

PFLEGEGELD = Benefit(
    id="pflegegeld", name_de="Pflegegeld", area="D", provider="PVA",
    summary_de="Monatliche Geldleistung bei ständigem Pflegebedarf von voraussichtlich mindestens sechs Monaten (Stufe 1–7).",
    plain_de="Geld jeden Monat, wenn jemand lange Hilfe im Alltag braucht.",
    form_ids=["pva_pflegegeld_pal080"],
    required_documents_de=["Aktuelle Befunde (z. B. Entlassungsbrief) in Kopie", "ggf. Vollmacht/Nachweis der Vertretung"],
    legal_basis=[BPGG4], sources=[VAL_PG1],
)

ANNA_ELIGIBILITY = [
    EligibilityResult(
        benefit=PFLEGEGELD, status=EligibilityStatus.needs_info,
        criteria=[
            CriterionResult(id="pg_6m", label_de="Pflegebedarf voraussichtlich ≥ 6 Monate", met=None,
                            explanation_de="Im Entlassungsbrief ist ein längerfristiger Unterstützungsbedarf dokumentiert; die Dauer stellt die PVA fest.", source=BPGG4),
            CriterionResult(id="pg_65h", label_de="Pflegebedarf > 65 Stunden/Monat (Stufe 1)", met=None,
                            explanation_de="Wird bei einem Hausbesuch durch die PVA begutachtet.", source=BPGG4),
        ],
        missing_fields=["care_hours_estimate"],
        next_steps_de=["Antrag auf Pflegegeld (PAL 080) ausfüllen", "Befundkopien beilegen", "Antrag an die PVA Landesstelle Wien senden"],
        amounts=[{"label_de": "Pflegegeld Stufe 1 (2026)", "value": 206.2, "unit": "EUR", "source": VAL_PG1.model_dump()}],
        rule_ids=["pflegegeld.v1"],
    )
]

STEFAN_PREVENTION = PreventionOverview(
    subject_id="stefan", as_of="2026-11-05",
    vaccinations=[
        VaccinationEntry(disease="Influenza", date="2025-11-03", vaccine="INFLUVAC TRI", dose_label="Auffrischung", place="1020 Wien"),
        VaccinationEntry(disease="COVID-19", date="2025-11-03", vaccine="COMIRNATY LP.8.1", dose_label="Auffrischung", place="1020 Wien"),
    ],
    items=[
        PreventionItem(id="flu", kind="vaccination", title_de="Influenza-Impfung (Saison 2026/27)", status=PreventionStatus.due,
                       last_date="2025-11-03", explanation_de="Die letzte dokumentierte Grippeimpfung war am 03.11.2025. Der Impfplan empfiehlt die Impfung jährlich im Herbst.",
                       cost_de="kostenlos", sources=[SourceRef(kind=SourceKind.brochure, label="Serviceratgeber 2026, S. 32", ref="page:32")]),
        PreventionItem(id="tdap", kind="vaccination", title_de="Diphtherie-Tetanus-Pertussis-Polio", status=PreventionStatus.not_documented,
                       explanation_de="Im e-Impfpass ist dazu keine Impfung eingetragen. Bitte klären Sie Ihren Impfstatus mit Ihrer Ärztin bzw. Ihrem Arzt."),
        PreventionItem(id="vu", kind="screening", title_de="Vorsorgeuntersuchung", status=PreventionStatus.due,
                       explanation_de="Ab 18 Jahren einmal jährlich kostenlos möglich.", cost_de="kostenlos",
                       sources=[SourceRef(kind=SourceKind.brochure, label="Serviceratgeber 2026, S. 23", ref="page:23")]),
    ],
)

ANNA_CASE = Case(
    id="case-anna", subject_id="anna", title_de="Versorgung nach Spitalsaufenthalt (Okt. 2026)", created_at="2026-11-05T10:00:00+00:00",
    steps=[CaseStep(id=f"s{i}", title_de=t, responsible_de=r) for i, (t, r) in enumerate([
        ("Termin zur hausärztlichen Kontrolle vereinbaren", "Patientin bzw. Vertrauensperson"),
        ("Pflegegeldanspruch prüfen / Antrag stellen", "Patientin mit Unterstützung"),
        ("Mobile Hauskrankenpflege organisieren (FSW)", "Entlassungsmanagement und soziale Dienste"),
        ("Rehabilitationsantrag vorbereiten", "Behandelnde Ärztin bzw. Arzt"),
        ("Fahrtmöglichkeiten zu Behandlungsterminen klären", "Patientin, Kostenträger"),
        ("Rezeptgebührenbefreiung prüfen", "Patientin bzw. ÖGK"),
    ], start=1)],
)

NOTIFICATIONS = [
    Notification(id="n1", subject_id="stefan", kind="prevention", created_at="2026-11-05T08:00:00+00:00",
                 title_de="Grippeimpfung: Saison 2026/27", body_de="Ihre letzte dokumentierte Grippeimpfung war am 03.11.2025.", link="/prevention"),
]

OFFICES = [
    Office(id="pva-wien", name="PVA Landesstelle Wien", provider="PVA", topics=["pflegegeld"],
           address="Friedrich-Hillegeist-Straße 1", zip="1020", city="Wien", phone="+43 5 0303",
           email="pva-lsw@pv.at", source=SourceRef(kind=SourceKind.form, label="PAL 080, S. 8", ref="pva_pflegegeld_pal080")),
    Office(id="fsw", name="Fonds Soziales Wien – Beratungszentrum Pflege und Betreuung", provider="FSW",
           topics=["mobile_pflege", "pflege"], address="Guglgasse 7–9", zip="1030", city="Wien", phone="+43 1 24 5 24",
           source=SourceRef(kind=SourceKind.form, label="FSW Antrag auf Förderung", ref="fsw_foerderung")),
]
