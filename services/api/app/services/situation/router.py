"""situation — Lebenslage (episodes + effects). STUB (owner: WS-S)."""

from fastapi import APIRouter, Depends, HTTPException

from app.contracts.identity import Scope
from app.contracts.situation import Episode, EpisodeCreate, EpisodeUpdate, SituationOverview
from app.core.auth import Context, require
from app.core.db import now_iso

router = APIRouter(prefix="/api/situation", tags=["situation"])
SCOPE = Scope.manage_situation


@router.get("", response_model=SituationOverview, summary="Current Lebenslage: episodes, suggestions, effects")
def overview(ctx: Context = Depends(require(SCOPE))):
    return SituationOverview(subject_id=ctx.subject.id, as_of=now_iso())  # STUB


@router.post("/episodes", response_model=Episode, summary="Add an episode (set by the person/representative)")
def add(body: EpisodeCreate, ctx: Context = Depends(require(SCOPE))):
    raise HTTPException(501, "Noch nicht verfügbar")  # STUB


@router.patch("/episodes/{episode_id}", response_model=Episode, summary="Change dates/status (e.g. end an episode)")
def update(episode_id: str, body: EpisodeUpdate, ctx: Context = Depends(require(SCOPE))):
    raise HTTPException(404, "Episode nicht gefunden")  # STUB


@router.delete("/episodes/{episode_id}", summary="Remove an episode entered by mistake")
def delete(episode_id: str, ctx: Context = Depends(require(SCOPE))):
    raise HTTPException(404, "Episode nicht gefunden")  # STUB


@router.post("/suggestions/from-document/{document_id}", response_model=list[Episode],
             summary="Suggest episodes from an analysed document (NOT applied until confirmed)")
def suggest(document_id: str, ctx: Context = Depends(require(SCOPE))):
    return []  # STUB


@router.post("/suggestions/{episode_id}/confirm", response_model=Episode, summary="Consent: apply a suggestion")
def confirm(episode_id: str, ctx: Context = Depends(require(SCOPE))):
    raise HTTPException(404, "Vorschlag nicht gefunden")  # STUB


@router.post("/suggestions/{episode_id}/reject", response_model=Episode, summary="Decline a suggestion")
def reject(episode_id: str, ctx: Context = Depends(require(SCOPE))):
    raise HTTPException(404, "Vorschlag nicht gefunden")  # STUB
