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


class BundleItem(BaseModel):
    kind: str                         # benefit | offer | prevention | appointment | office | form | case
    ref_id: str                       # benefit id / prevention item id / provider topic / form id …
    title_de: str
    why_de: str                       # why this is relevant here (administrative, never medical)
    status: EligibilityStatus | None = None
    status_de: str | None = None      # plain status label, e.g. "jetzt fällig", "kostenlos nutzbar", "kommt voraussichtlich in Frage"
    source: SourceRef | None = None


class Bundle(BaseModel):
    """'Bündel' for a life situation: everything relevant, ordered, with the next concrete step."""
    id: str                           # pflege_zuhause | nach_spital | gesundheit_foerdern | kind | finanzielle_unterstuetzung
    title_de: str
    situation_de: str
    items: list[BundleItem]
    questions_de: list[str] = []      # targeted follow-up questions that unlock more items (max 2–3)
    next_step_de: str = ""


class BundleRequest(BaseModel):
    situation: str | None = None      # bundle id, or None = detect from text
    text: str | None = None           # free text ("Meine Mutter braucht jetzt Hilfe …") for deterministic matching
    facts: dict = {}
    document_ids: list[str] = []
