"""notifications — proactive inbox. STUB (owner: WS-C)."""

from fastapi import APIRouter, Depends

from app.contracts.misc import Notification
from app.core.auth import Context, require
from app.fixtures import NOTIFICATIONS

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=list[Notification])
def inbox(ctx: Context = Depends(require())):
    return [n for n in NOTIFICATIONS if n.subject_id == ctx.subject.id]  # STUB


@router.post("/{notification_id}/read", response_model=Notification | None)
def mark_read(notification_id: str, ctx: Context = Depends(require())):
    return next((n.model_copy(update={"read": True}) for n in NOTIFICATIONS if n.id == notification_id), None)
