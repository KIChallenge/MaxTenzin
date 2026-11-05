from enum import StrEnum

from pydantic import BaseModel

from app.contracts.common import SourceRef


class EligibilityStatus(StrEnum):
    likely = "likely"                 # all known criteria met
    possible = "possible"             # plausible, decision by Träger
    needs_info = "needs_info"         # missing facts -> see missing_fields
    not_applicable = "not_applicable"


class Benefit(BaseModel):
    id: str                           # e.g. "pflegegeld"
    name_de: str
    area: str                         # A–F areas from the challenge (Vorsorge, Pflege, ...)
    summary_de: str
    plain_de: str = ""                # Einfache Sprache
    provider: str                     # zuständiger Träger, e.g. "PVA", "ÖGK", "FSW"
    form_ids: list[str] = []
    required_documents_de: list[str] = []
    legal_basis: list[SourceRef] = []
    sources: list[SourceRef] = []


class CriterionResult(BaseModel):
    id: str
    label_de: str
    met: bool | None                  # None = unknown
    explanation_de: str
    source: SourceRef | None = None


class EligibilityResult(BaseModel):
    benefit: Benefit
    status: EligibilityStatus
    criteria: list[CriterionResult]
    missing_fields: list[str] = []    # facts the agent should ask for
    next_steps_de: list[str] = []
    amounts: list[dict] = []          # e.g. [{"label_de": "Pflegegeld Stufe 1", "value": 206.2, "unit": "EUR", "source": SourceRef}]
    rule_ids: list[str] = []          # for audit


class EligibilityRequest(BaseModel):
    subject_id: str
    facts: dict = {}                  # known facts (e.g. {"care_need_months": 6, "net_income_monthly": 1200})
    document_ids: list[str] = []      # use recommendations from these documents
    benefit_ids: list[str] | None = None
