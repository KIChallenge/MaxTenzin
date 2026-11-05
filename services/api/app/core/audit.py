"""Audit middleware: every API call (UI or agent) is logged with actor, subject, tool, scope and cited sources."""

from __future__ import annotations

import json

from sqlmodel import Session
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.db import AuditRow, engine, now_iso

SKIP_PREFIXES = ("/docs", "/openapi.json", "/redoc", "/api/health", "/api/audit")


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path.startswith(SKIP_PREFIXES) or request.method == "OPTIONS":
            return response
        ctx = getattr(request.state, "ctx", None)
        row = AuditRow(
            ts=now_iso(),
            actor_id=ctx.actor.id if ctx else None,
            subject_id=ctx.subject.id if ctx else None,
            via=request.headers.get("X-Via", "ui"),
            tool=request.headers.get("X-Agent-Tool"),
            method=request.method,
            path=path,
            status=response.status_code,
            scope_required=getattr(request.state, "scope_required", None),
            allowed=getattr(request.state, "allowed", response.status_code != 403),
            sources_json=json.dumps(ctx.sources if ctx else [], ensure_ascii=False),
            rule_ids_json=json.dumps(ctx.rule_ids if ctx else [], ensure_ascii=False),
        )
        with Session(engine()) as s:
            s.add(row)
            s.commit()
        return response
