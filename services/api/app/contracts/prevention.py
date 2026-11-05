from enum import StrEnum

from pydantic import BaseModel

from app.contracts.common import SourceRef


class VaccinationEntry(BaseModel):
    disease: str                      # e.g. "Influenza", "COVID-19"
    date: str                         # ISO date
    vaccine: str
    dose_label: str = ""              # "Dosis 1", "Auffrischung"
    place: str = ""


class PreventionStatus(StrEnum):
    due = "due"
    upcoming = "upcoming"
    up_to_date = "up_to_date"
    not_documented = "not_documented"  # NEVER phrase as 'missing' to the user


class PreventionItem(BaseModel):
    id: str
    kind: str                         # "vaccination" | "screening"
    title_de: str
    status: PreventionStatus
    due_date: str | None = None
    last_date: str | None = None
    explanation_de: str               # always ends with advice to discuss with doctor where relevant
    cost_de: str = ""                 # e.g. "kostenlos (ÖGK)"
    sources: list[SourceRef] = []


class PreventionOverview(BaseModel):
    subject_id: str
    as_of: str
    vaccinations: list[VaccinationEntry]
    items: list[PreventionItem]
    disclaimer_de: str = "Hinweise laut Österreichischem Impfplan und ÖGK-Angeboten – keine medizinische Beratung. Bitte besprechen Sie Ihren Impfstatus mit Ihrer Ärztin bzw. Ihrem Arzt."
