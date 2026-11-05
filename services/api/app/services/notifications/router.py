"""notifications — proactive inbox, computed from other services via their HTTP APIs with the user's own token.

Scopes therefore apply transitively: no 'view_health_prevention' for this subject -> no prevention notifications.
REAL (WS-C).
"""

import httpx
from fastapi import APIRouter, Depends, Request

from app.contracts.misc import Notification
from app.core.auth import Context, require
from app.core.db import now_iso, store

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


async def _call(request: Request, path: str) -> httpx.Response:
    from app.main import app  # lazy: avoid import cycle

    headers = {k: v for k, v in request.headers.items() if k.lower() in ("authorization", "x-subject-id")}
    headers["X-Via"] = "service:notifications"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://internal") as c:
        return await c.get(path, headers=headers)


def _is_read(subject_id: str, nid: str) -> bool:
    return bool(store.get("notification_reads", f"{subject_id}:{nid}"))


@router.get("", response_model=list[Notification], summary="Proactive notifications for the current subject")
async def inbox(request: Request, ctx: Context = Depends(require())):
    out: list[Notification] = []
    sid = ctx.subject.id
    prev = await _call(request, "/api/prevention/overview")
    if prev.status_code == 200:
        for item in prev.json()["items"]:
            if item["status"] in ("due", "not_documented"):
                nid = f"prev-{item['id']}"
                out.append(Notification(id=nid, subject_id=sid, kind="prevention", created_at=now_iso(),
                                        title_de=item["title_de"], body_de=item["explanation_de"], link="/prevention",
                                        read=_is_read(sid, nid)))
    cases = await _call(request, "/api/cases")
    if cases.status_code == 200:
        for case in cases.json():
            open_steps = [s for s in case["steps"] if s["status"] in ("open", "in_progress")]
            if open_steps:
                nid = f"case-{case['id']}"
                out.append(Notification(id=nid, subject_id=sid, kind="case", created_at=now_iso(),
                                        title_de=f"{len(open_steps)} offene Schritte: {case['title_de']}",
                                        body_de=f"Nächster Schritt: {open_steps[0]['title_de']}", link="/case",
                                        read=_is_read(sid, nid)))
    return out


@router.post("/{notification_id}/read", summary="Mark a notification as read")
def mark_read(notification_id: str, ctx: Context = Depends(require())):
    store.put("notification_reads", f"{ctx.subject.id}:{notification_id}", {"read": True}, subject_id=ctx.subject.id)
    return {"id": notification_id, "read": True}
