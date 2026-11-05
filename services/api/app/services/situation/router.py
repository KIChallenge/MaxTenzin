"""situation — Lebenslage: episodes (hospital, rehab, therapy, home care …), document suggestions with consent, effects.

Episodes are set by the person/representative. Documents only create SUGGESTIONS that take effect after /confirm.
Confirmed episodes drive deterministic effects (reminders, eligibility facts, form prefill, Mein-Fall steps).
Owner: WS-S.
"""

from __future__ import annotations

import uuid
from datetime import date

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.contracts.identity import Scope
from app.contracts.situation import (
    Episode,
    EpisodeCreate,
    EpisodeStatus,
    EpisodeType,
    EpisodeUpdate,
    SituationOverview,
)
from app.core.auth import Context, require
from app.core.db import now_iso, store
from app.services.situation import service as svc

router = APIRouter(prefix="/api/situation", tags=["situation"])
SCOPE = Scope.manage_situation
NOT_FOUND = "Episode nicht gefunden"
SUGGESTION_NOT_FOUND = "Vorschlag nicht gefunden"


def _today(as_of: str | None = None) -> date:
    if not as_of:
        return date.today()
    try:
        return date.fromisoformat(as_of)
    except ValueError as exc:
        raise HTTPException(422, "as_of muss ein ISO-Datum sein (JJJJ-MM-TT).") from exc


def _actor_name(ctx: Context) -> str:
    return f"{ctx.actor.first_name} {ctx.actor.last_name}"


def _check_dates(start: str | None, end: str | None) -> None:
    for v in (start, end):
        if v is not None and v != "":
            try:
                date.fromisoformat(v)
            except ValueError as exc:
                raise HTTPException(422, "Datum bitte im Format JJJJ-MM-TT angeben.") from exc
    if start and end and end < start:
        raise HTTPException(422, "Das Ende liegt vor dem Beginn.")


def _check_subtype(type_: EpisodeType, subtype: str | None) -> None:
    if subtype and (type_ != EpisodeType.therapy or subtype not in svc.cfg()["therapy_subtypes"]):
        allowed = ", ".join(svc.cfg()["therapy_subtypes"])
        raise HTTPException(422, f"Untertyp nur bei Therapie möglich: {allowed}.")


def _cite(ctx: Context, ep: Episode) -> None:
    ctx.cite(ep.source.label)
    ctx.rule_ids.append("situation.v1")


async def _sync_case_steps(request: Request, ctx: Context) -> list[str]:
    """Add situation steps to the subject's most recent case (if any). The case list is read via the cases API with
    the user's own token, so the manage_case scope applies; without it nothing is added."""
    from app.main import app  # lazy: avoid import cycle

    headers = {k: v for k, v in request.headers.items() if k.lower() in ("authorization", "x-subject-id")}
    headers["X-Via"] = "service:situation"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://internal") as c:
        res = await c.get("/api/cases", headers=headers)
    if res.status_code != 200:
        return []
    case = svc.latest_case(ctx.subject.id, res.json())
    if case is None:
        return []
    today = date.today()
    eps = svc.confirmed(ctx.subject.id, today)
    steps = svc.case_steps_from(eps, today, svc.pflegegeld_involved(ctx.subject.id))
    have = {s["id"] for s in case.get("steps", [])}
    probe = {"steps": list(case.get("steps", []))}
    added = svc.add_case_steps(probe, steps)  # builds step dicts in contract shape, idempotent by id
    if added:
        new_steps = [s for s in probe["steps"] if s["id"] in added and s["id"] not in have]
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://internal") as c:
            r = await c.post(f"/api/cases/{case['id']}/steps", headers=headers, json=new_steps)
        if r.status_code != 200:
            return []
        ctx.rule_ids.append(f"situation.case_steps:{case['id']}:{len(added)}")
    return added


@router.get("", response_model=SituationOverview, summary="Current Lebenslage: episodes, suggestions, effects")
def overview(as_of: str | None = Query(None, description="Stichtag (ISO), default heute"),
             ctx: Context = Depends(require(SCOPE))):
    ov = svc.overview(ctx.subject.id, _today(as_of))
    ctx.cite(*{e.source.label for e in ov.effects if e.source})
    ctx.rule_ids.append("situation.v1")
    return ov


@router.post("/episodes", response_model=Episode, summary="Add an episode (set by the person/representative)")
async def add(body: EpisodeCreate, request: Request, ctx: Context = Depends(require(SCOPE))):
    _check_dates(body.start, body.end)
    _check_subtype(body.type, body.subtype)
    today = date.today()
    raw = {
        "id": f"ep-{uuid.uuid4().hex[:8]}",
        "subject_id": ctx.subject.id, "type": body.type.value, "subtype": body.subtype,
        "title_de": body.title_de or svc.title_for(body.type, body.subtype),
        "start": body.start or None, "end": body.end or None, "end_estimate_de": body.end_estimate_de,
        "institution": body.institution, "note_de": body.note_de, "status": svc.CONFIRMED,
        "source": svc.person_source(_actor_name(ctx), today).model_dump(),
        "created_by": ctx.actor.id, "confirmed_by": ctx.actor.id, "confirmed_at": now_iso(),
    }
    svc.put_raw(raw)
    await _sync_case_steps(request, ctx)
    ep = svc.to_episode(raw, today)
    _cite(ctx, ep)
    return ep


@router.patch("/episodes/{episode_id}", response_model=Episode, summary="Change dates/status (e.g. end an episode)")
async def update(episode_id: str, body: EpisodeUpdate, request: Request, ctx: Context = Depends(require(SCOPE))):
    raw = svc.get_raw(ctx.subject.id, episode_id)
    if raw is None:
        raise HTTPException(404, NOT_FOUND)
    patch = body.model_dump(exclude_unset=True)
    status = patch.pop("status", None)
    merged = {**raw, **patch}
    if "institution" in patch:
        merged["institution_source"] = None   # the document quote no longer backs a value the person changed
    _check_dates(merged.get("start"), merged.get("end"))
    if status in (EpisodeStatus.suggested, EpisodeStatus.rejected):
        raise HTTPException(422, "Vorschläge bitte über /confirm bzw. /reject bestätigen oder ablehnen.")
    today = date.today()
    if status is not None:
        if raw.get("status") != svc.CONFIRMED:
            raise HTTPException(409, "Bitte den Vorschlag zuerst bestätigen.")
        merged["manual_status"] = status.value
        if status == EpisodeStatus.ended and not merged.get("end"):
            merged["end"] = today.isoformat()
        if status != EpisodeStatus.ended and merged.get("end") and svc.parse_date(merged["end"]) < today:
            merged["end"] = None   # re-opened
    svc.put_raw(merged)
    if merged.get("status") == svc.CONFIRMED:
        await _sync_case_steps(request, ctx)
    ep = svc.to_episode(merged, today)
    _cite(ctx, ep)
    return ep


@router.delete("/episodes/{episode_id}", summary="Remove an episode entered by mistake")
def delete(episode_id: str, ctx: Context = Depends(require(SCOPE))):
    if svc.get_raw(ctx.subject.id, episode_id) is None:
        raise HTTPException(404, NOT_FOUND)
    store.delete(svc.COLL, episode_id)
    return {"id": episode_id, "deleted": True}


@router.post("/suggestions/from-document/{document_id}", response_model=list[Episode],
             summary="Suggest episodes from an analysed document (NOT applied until confirmed)")
def suggest(document_id: str, ctx: Context = Depends(require(SCOPE))):
    if Scope.read_documents not in ctx.scopes:
        raise HTTPException(403, f"Fehlende Berechtigung 'read_documents' für {ctx.subject.first_name} "
                                 f"{ctx.subject.last_name}.")
    a = svc.load_analysis(ctx.subject.id, document_id)
    if a is None:
        raise HTTPException(404, "Für dieses Dokument liegt noch keine Analyse vor.")
    today = date.today()
    out: list[Episode] = []
    for s in svc.suggest_from_analysis(a, svc.document_pages(ctx.subject.id, document_id)):
        sid = svc.suggestion_id(document_id, s.pop("rule"))
        raw = svc.get_raw(ctx.subject.id, sid)
        if raw is None:   # idempotent: an existing suggestion (any state) is never duplicated or reset
            if store.get(svc.COLL, sid) is not None:
                continue   # id taken by another subject (cannot happen with subject-owned documents)
            # Same episode from another copy of the document (photo + PDF) or already entered: don't suggest again.
            twin = next((r for r in svc.raw_episodes(ctx.subject.id)
                         if r["type"] == s["type"].value and r.get("subtype") == s.get("subtype")
                         and r.get("end") == s.get("end") and r.get("start") == s.get("start")), None)
            if twin is not None:
                out.append(svc.to_episode(twin, today))
                continue
            raw = {"id": sid, "subject_id": ctx.subject.id, "subtype": None, "start": None, "end": None,
                   "end_estimate_de": None, "institution": None, "note_de": None, **s,
                   "type": s["type"].value, "title_de": svc.title_for(s["type"], s.get("subtype")),
                   "status": EpisodeStatus.suggested.value, "source": s["source"].model_dump(),
                   "institution_source": s["institution_source"].model_dump() if s.get("institution_source") else None,
                   "created_by": ctx.actor.id, "confirmed_by": None, "confirmed_at": None,
                   "manual_status": s.get("manual_status").value if s.get("manual_status") else None}
            svc.put_raw(raw)
        out.append(svc.to_episode(raw, today))
    ctx.cite(*{e.source.label for e in out})
    ctx.rule_ids.append("situation.suggest.v1")
    return out


@router.post("/suggestions/{episode_id}/confirm", response_model=Episode, summary="Consent: apply a suggestion")
async def confirm(episode_id: str, request: Request, ctx: Context = Depends(require(SCOPE))):
    raw = svc.get_raw(ctx.subject.id, episode_id)
    if raw is None or raw.get("status") not in (EpisodeStatus.suggested, EpisodeStatus.rejected, svc.CONFIRMED):
        raise HTTPException(404, SUGGESTION_NOT_FOUND)
    if raw["status"] != svc.CONFIRMED:   # idempotent: confirming twice keeps the first consent
        raw.update(status=svc.CONFIRMED, confirmed_by=ctx.actor.id, confirmed_at=now_iso())
        svc.put_raw(raw)
    await _sync_case_steps(request, ctx)
    ep = svc.to_episode(raw, date.today())
    _cite(ctx, ep)
    return ep


@router.post("/suggestions/{episode_id}/reject", response_model=Episode, summary="Decline a suggestion")
def reject(episode_id: str, ctx: Context = Depends(require(SCOPE))):
    raw = svc.get_raw(ctx.subject.id, episode_id)
    if raw is None or raw.get("status") not in (EpisodeStatus.suggested, EpisodeStatus.rejected):
        raise HTTPException(404, SUGGESTION_NOT_FOUND)
    raw["status"] = EpisodeStatus.rejected.value
    svc.put_raw(raw)
    return svc.to_episode(raw, date.today())
