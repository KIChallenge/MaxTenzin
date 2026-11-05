"""Smaller service contracts: notifications, directory, medications, legal, values, audit."""

from pydantic import BaseModel

from app.contracts.common import SourceRef


class Notification(BaseModel):
    id: str
    subject_id: str
    title_de: str
    body_de: str
    kind: str                         # prevention | case | info
    created_at: str
    read: bool = False
    link: str | None = None


class Office(BaseModel):
    id: str
    name: str
    provider: str                     # ÖGK | PVA | FSW | 1450 ...
    topics: list[str]                 # pflegegeld, reha, rezeptgebuehr, mobile_pflege ...
    address: str
    zip: str
    city: str
    phone: str = ""
    email: str = ""
    web: str = ""
    source: SourceRef


class Medication(BaseModel):
    pharma_nr: str
    name: str
    box: str                          # G | Y
    restriction: str
    pack: str
    price_eur: float | None
    approval_needed_de: str           # administrative explanation only
    patient_cost_note_de: str         # Rezeptgebühr vs price
    rule_text: str | None = None
    indication_text: str | None = None
    source: SourceRef


class LegalParagraph(BaseModel):
    doc_id: str
    law_key: str
    law: str
    law_title: str
    nr: str
    heading: str
    text: str
    in_force: str
    citation_de: str                  # e.g. "§ 4 BPGG (in Kraft seit 01.01.2015)"


class LegalHit(BaseModel):
    paragraph: LegalParagraph
    score: float
    snippet: str


class Value(BaseModel):
    key: str
    label_de: str
    year: int
    value: float
    unit: str
    legal_ref: str
    source: SourceRef


class AuditEvent(BaseModel):
    id: int
    ts: str
    actor_id: str | None
    subject_id: str | None
    via: str                          # "ui" | "agent"
    tool: str | None                  # agent tool name if via agent
    method: str
    path: str
    status: int
    scope_required: str | None = None
    allowed: bool = True
    sources: list[str] = []           # citations used in the response
    rule_ids: list[str] = []
