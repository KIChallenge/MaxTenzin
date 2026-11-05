from enum import StrEnum

from pydantic import BaseModel

from app.contracts.common import SourceRef


class StepStatus(StrEnum):
    open = "open"
    in_progress = "in_progress"
    done = "done"
    blocked = "blocked"


class CaseStep(BaseModel):
    id: str
    title_de: str
    responsible_de: str               # who does it (Patientin, Hausärztin, PVA ...)
    status: StepStatus = StepStatus.open
    benefit_id: str | None = None
    form_session_id: str | None = None
    due_date: str | None = None
    source: SourceRef | None = None


class Case(BaseModel):
    id: str
    subject_id: str
    title_de: str
    created_at: str
    steps: list[CaseStep]


class CaseCreate(BaseModel):
    subject_id: str
    title_de: str
    document_id: str | None = None    # seed steps from document open_tasks
    benefit_ids: list[str] = []


class StepUpdate(BaseModel):
    status: StepStatus | None = None
    form_session_id: str | None = None    # link a started application to this step
