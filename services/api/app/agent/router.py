"""agent — AI top layer (tool calling over the service APIs). STUB (owner: WS-A)."""

import uuid

from fastapi import APIRouter, Depends

from app.contracts.agent import ChatRequest, ChatResponse
from app.core.auth import Context, require
from app.core.llm import get_llm

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/chat", response_model=ChatResponse, summary="Chat with the KI-Lotse")
def chat(req: ChatRequest, ctx: Context = Depends(require())):
    msg = get_llm().chat([{"role": "user", "content": req.message}])  # STUB: no tools yet
    return ChatResponse(conversation_id=req.conversation_id or uuid.uuid4().hex[:8], reply=msg.content or "")
