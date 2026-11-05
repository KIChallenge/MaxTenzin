from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str                         # user | assistant
    content: str


class ToolTrace(BaseModel):
    tool: str
    arguments: dict
    status: int
    summary_de: str
    sources: list[str] = []


class ChatAction(BaseModel):
    """UI action produced by a tool call (e.g. download the rendered draft, open the wizard)."""
    kind: str                         # download_pdf | open_form | open_case
    label_de: str
    method: str = "GET"
    url: str                          # API path (download) or app route (open_*)


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str
    language: str = "de"
    plain_language: bool = False
    document_ids: list[str] = []      # documents currently selected in the UI (context hint, access still via API)


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    tool_trace: list[ToolTrace] = []
    boundary_triggered: bool = False  # medical boundary guard fired
    suggestions_de: list[str] = []    # quick-reply chips
    actions: list[ChatAction] = []    # buttons for the UI (download draft, open wizard, open case)
