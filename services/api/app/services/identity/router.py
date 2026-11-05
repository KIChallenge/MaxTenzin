"""identity — mock ID Austria login, persona list, delegations (Vertretung) with scopes. REAL (integrator-owned)."""

from fastapi import APIRouter, Depends, HTTPException

from app.contracts.identity import Delegation, LoginRequest, Person, Scope, Session
from app.core.auth import TOKEN_PREFIX, Context, effective_scopes, get_context
from app.seed.loader import (
    all_persons,
    delegations_for,
    delegations_of_grantee,
    get_person,
    set_delegation_scopes,
)

router = APIRouter(prefix="/api/identity", tags=["identity"])


@router.get("/personas", response_model=list[Person], summary="Demo personas (mock ID Austria)")
def personas():
    return all_persons()


@router.post("/login", response_model=Session, summary="Mock ID Austria login")
def login(req: LoginRequest):
    p = get_person(req.persona_id)
    if not p:
        raise HTTPException(404, "Persona unbekannt")
    return Session(token=f"{TOKEN_PREFIX}{p.id}", actor=p, subject=p, scopes=sorted(Scope),
                   delegations=delegations_of_grantee(p.id))


@router.get("/me", response_model=Session, summary="Current actor, subject and effective scopes")
def me(ctx: Context = Depends(get_context)):
    return Session(token=f"{TOKEN_PREFIX}{ctx.actor.id}", actor=ctx.actor, subject=ctx.subject,
                   scopes=sorted(ctx.scopes), delegations=delegations_of_grantee(ctx.actor.id))


@router.get("/represented", response_model=list[Person], summary="Persons the actor may act for (incl. self)")
def represented(ctx: Context = Depends(get_context)):
    return [ctx.actor] + [get_person(d.grantor_id) for d in delegations_of_grantee(ctx.actor.id)]


@router.get("/delegations", response_model=list[Delegation], summary="Delegations granted by the subject")
def delegations(ctx: Context = Depends(get_context)):
    return delegations_for(ctx.subject.id)


@router.put("/delegations/{delegation_id}/scopes", response_model=Delegation, summary="Grantor changes scopes (demo)")
def update_scopes(delegation_id: str, scopes: list[Scope], ctx: Context = Depends(get_context)):
    d = next((d for d in delegations_for(ctx.actor.id) if d.id == delegation_id), None)
    if d is None and ctx.actor.id != ctx.subject.id:
        raise HTTPException(403, "Nur die vertretene Person kann Berechtigungen ändern.")
    # demo convenience: grantee may also reduce (never extend) own scopes
    target = d or next((x for x in delegations_of_grantee(ctx.actor.id) if x.id == delegation_id), None)
    if target is None:
        raise HTTPException(404, "Vertretung nicht gefunden")
    if d is None and not set(scopes) <= set(target.scopes):
        raise HTTPException(403, "Berechtigungen können nur von der vertretenen Person erweitert werden.")
    return set_delegation_scopes(delegation_id, scopes)


__all__ = ["effective_scopes", "router"]
