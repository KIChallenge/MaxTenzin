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


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str
    language: str = "de"
    plain_language: bool = False


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    tool_trace: list[ToolTrace] = []
    boundary_triggered: bool = False  # medical boundary guard fired
    suggestions_de: list[str] = []    # quick-reply chips
