"""audit — read the transparency log. (integrator-owned)."""

import json

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.contracts.misc import AuditEvent
from app.core.auth import Context, get_context
from app.core.db import AuditRow, engine

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=list[AuditEvent], summary="Audit events for the current subject (newest first)")
def list_events(limit: int = 100, ctx: Context = Depends(get_context)):
    with Session(engine()) as s:
        rows = s.exec(select(AuditRow).where(AuditRow.subject_id == ctx.subject.id).order_by(AuditRow.id.desc()).limit(limit)).all()
    return [AuditEvent(id=r.id, ts=r.ts, actor_id=r.actor_id, subject_id=r.subject_id, via=r.via, tool=r.tool, method=r.method,
                       path=r.path, status=r.status, scope_required=r.scope_required, allowed=r.allowed,
                       sources=json.loads(r.sources_json), rule_ids=json.loads(r.rule_ids_json)) for r in rows]
