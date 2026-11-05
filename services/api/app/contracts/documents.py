from enum import StrEnum

from pydantic import BaseModel, Field


class RecommendationCategory(StrEnum):
    rehabilitation = "rehabilitation"
    care = "care"                 # Pflege / Pflegegeld / mobile Dienste
    follow_up = "follow_up"       # Kontrolltermine / Nachsorge
    transport = "transport"
    costs = "costs"               # Rezeptgebühr, Zuschüsse
    aids = "aids"                 # Heilbehelfe / Hilfsmittel
    nutrition = "nutrition"
    other = "other"


class Recommendation(BaseModel):
    """An EXPLICITLY documented recommendation. Never inferred, never interpreted."""
    id: str
    text_de: str = Field(..., description="Neutral restatement: 'Im Dokument wird ... empfohlen.'")
    quote: str = Field(..., description="Verbatim quote from the document")
    page: int
    category: RecommendationCategory
    related_benefit_ids: list[str] = []


class DocumentFact(BaseModel):
    """Administrative fact found deterministically in a document (never medical content), with quote + page."""
    key: str                          # e.g. discharge_date, department
    value: str
    quote: str
    page: int


class ExtractedPerson(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    birth_date: str | None = None
    address: str | None = None
    insurer: str | None = None
    living_situation: str | None = None


class DocumentType(StrEnum):
    discharge_letter = "discharge_letter"
    imaging_report = "imaging_report"
    vaccination_record = "vaccination_record"
    other = "other"


class DocumentAnalysis(BaseModel):
    document_id: str
    filename: str
    doc_type: DocumentType
    pages: int
    person: ExtractedPerson
    recommendations: list[Recommendation]
    open_tasks: list[str] = Field([], description="Tasks explicitly listed in the document (e.g. Entlassungsbrief §9)")
    notice_de: str = Field(
        "Ich gebe nur wieder, was im Dokument ausdrücklich steht. Medizinische Fragen klären Sie bitte mit Ihrer Ärztin bzw. Ihrem Arzt.",
    )
    extraction_mode: str = "live"   # live | golden | fake
    facts: list[DocumentFact] = Field([], description="Deterministic administrative facts (e.g. Entlassungsdatum)")
    dropped_unverified: int = Field(0, description="Recommendations discarded because their quote was not found on the stated page")


class DocumentSummary(BaseModel):
    document_id: str
    filename: str
    doc_type: DocumentType
    uploaded_at: str
    owner_id: str
