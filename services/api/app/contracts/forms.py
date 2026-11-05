from enum import StrEnum

from pydantic import BaseModel

from app.contracts.common import SourceRef


class FieldType(StrEnum):
    text = "text"
    date = "date"
    checkbox = "checkbox"
    choice = "choice"
    textarea = "textarea"


class FieldCondition(BaseModel):
    """Field is relevant only if the condition holds (same shape as the form spec). proxy: actor acts for someone else."""
    field: str | None = None
    equals: str | bool | None = None
    one_of: list[str] = []
    proxy: bool | None = None


class FormField(BaseModel):
    id: str
    label_de: str
    type: FieldType
    section: str
    required: bool = False
    ask_hint_de: str = ""             # plain-language question the agent/wizard asks
    options: list[str] = []
    readonly_reason_de: str | None = None   # e.g. doctor-only sections
    when: FieldCondition | None = None       # show/ask only if this holds


class FormDefinition(BaseModel):
    form_id: str
    title_de: str
    provider: str
    sections: list[str]
    fields: list[FormField]
    submit_info_de: str               # where/how the user submits it themselves


class FieldValue(BaseModel):
    value: str | bool | None
    source: SourceRef | None = None   # where the prefill came from (profile, document quote ...)
    confirmed: bool = False           # user confirmed in wizard/chat


class FormSession(BaseModel):
    id: str
    form_id: str
    subject_id: str
    actor_id: str
    document_id: str | None = None    # document the prefill was taken from (if any)
    values: dict[str, FieldValue]
    status: str = "draft"             # draft | ready | rendered  (never 'submitted')
    updated_at: str


class NextQuestions(BaseModel):
    session_id: str
    questions: list[FormField]        # only required + still empty
    progress: float                   # 0..1


class FieldPatch(BaseModel):
    values: dict[str, str | bool | None]
    confirm: bool = True
