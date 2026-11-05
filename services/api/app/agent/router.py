"""agent — AI top layer: tool calling over the service APIs with the user's own token. (owner: WS-A).

The agent has no special rights: it forwards the caller's Authorization + X-Subject-Id to every tool call.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.agent import state
from app.agent.orchestrator import handle_turn
from app.contracts.agent import ChatRequest, ChatResponse, ToolTrace
from app.core.auth import Context, require
from app.core.db import store

router = APIRouter(prefix="/api/agent", tags=["agent"])


# Agent-local view models (not shared contracts; see README "Contract requests").
class ConversationTurn(BaseModel):
    ts: str
    user: str
    reply: str
    tool_trace: list[ToolTrace] = []
    boundary_triggered: bool = False
    suggestions_de: list[str] = []
    latency_ms: int | None = None
    mode: str | None = None           # live | scripted | scripted-fallback | content-filter | boundary:<category>


class Conversation(BaseModel):
    id: str
    actor_id: str
    subject_id: str
    created_at: str
    updated_at: str | None = None
    turns: list[ConversationTurn] = []


def _forward_headers(request: Request) -> dict[str, str]:
    return {k: v for k, v in request.headers.items() if k.lower() in ("authorization", "x-subject-id")}


@router.post("/chat", response_model=ChatResponse, summary="Chat with Lotsi (KI-Lotse agent)")
async def chat(req: ChatRequest, request: Request, ctx: Context = Depends(require())):
    if not req.message.strip():
        raise HTTPException(422, "Bitte geben Sie eine Nachricht ein.")
    if len(req.message) > 4000:
        raise HTTPException(413, "Die Nachricht ist zu lang (max. 4000 Zeichen).")
    return await handle_turn(req, ctx, _forward_headers(request))


@router.get("/conversations", response_model=list[Conversation], summary="Conversations of the actor for the subject")
def list_conversations(ctx: Context = Depends(require())):
    return [c for c in store.list(state.COLL, subject_id=ctx.subject.id) if c["actor_id"] == ctx.actor.id]


@router.get("/conversations/{conversation_id}", response_model=Conversation, summary="Conversation history incl. traces")
def get_conversation(conversation_id: str, ctx: Context = Depends(require())):
    c = store.get(state.COLL, conversation_id)
    if not c or c["actor_id"] != ctx.actor.id or c["subject_id"] != ctx.subject.id:
        raise HTTPException(404, "Gespräch nicht gefunden")
    return c
