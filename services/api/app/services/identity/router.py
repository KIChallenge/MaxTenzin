"""identity — mock ID Austria login, persona list, delegations (Vertretung) with scopes. (integrator-owned)."""

from fastapi import APIRouter, Depends, HTTPException

from app.contracts.common import SourceKind, SourceRef
from app.contracts.identity import (
    CareTeam,
    CareTeamMember,
    Delegation,
    LoginRequest,
    Person,
    Preferences,
    Scope,
    Session,
    SetCareTeamMember,
)
from app.core.auth import TOKEN_PREFIX, Context, effective_scopes, get_context, require
from app.core.db import now_iso, store
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


# ---- Preferences (per acting person) --------------------------------------------------------------------------
@router.get("/preferences", response_model=Preferences, summary="Preferences of the acting person")
def get_preferences(ctx: Context = Depends(get_context)):
    data = store.get("preferences", ctx.actor.id)
    if data:
        return Preferences(**data)
    return Preferences(language=ctx.actor.language, plain_language=ctx.actor.plain_language)


@router.put("/preferences", response_model=Preferences, summary="Save preferences (language, detail, daypart …)")
def put_preferences(body: Preferences, ctx: Context = Depends(get_context)):
    store.put("preferences", ctx.actor.id, body.model_dump(), subject_id=ctx.actor.id)
    return body


# ---- Behandlungsteam (Hausärztin u. a.) -----------------------------------------------------------------------
ROLE_DE = {"hausarzt": "Hausärztin/Hausarzt", "kinderarzt": "Kinderärztin/Kinderarzt", "ambulanz": "Ambulanz"}


def _care_seed() -> dict:
    import yaml

    from app.seed.loader import HERE

    return yaml.safe_load((HERE / "care_team.yaml").read_text(encoding="utf-8")) or {}


def _member(m: dict, source: SourceRef) -> CareTeamMember | None:
    from app.services.appointments.service import providers

    p = next((x for x in providers() if x.id == m["provider_id"]), None)
    if p is None:
        return None
    return CareTeamMember(role=m["role"], role_de=m.get("role_de") or ROLE_DE.get(m["role"], m["role"]),
                          provider_id=p.id, name=p.name, address=f"{p.address}, {p.zip} {p.city}", phone=p.phone,
                          since=m.get("since"), source=source)


def _care_team(ctx: Context) -> CareTeam:
    members: dict[str, CareTeamMember] = {}
    for m in _care_seed().get(ctx.subject.id, []):
        src = SourceRef(kind=SourceKind.external, label="Profil (Demo) – im Echtbetrieb aus e-card-Konsultationen",
                        ref=f"care_team:{ctx.subject.id}#{m['role']}", quote=m.get("note"))
        if (x := _member(m, src)):
            members[m["role"]] = x
    for o in store.list("care_team_overrides", subject_id=ctx.subject.id):
        src = SourceRef(kind=SourceKind.external, label=f"Angabe von {o['set_by_name']}, {o['set_at'][:10]}",
                        ref=f"care_team:{ctx.subject.id}#{o['role']}")
        if (x := _member(o, src)):
            members[o["role"]] = x
    ctx.cite(*(m.source.label for m in members.values()))
    return CareTeam(subject_id=ctx.subject.id, members=list(members.values()))


@router.get("/care-team", response_model=CareTeam, summary="Behandlungsteam (Hausärztin u. a.) of the subject")
def care_team(ctx: Context = Depends(require(Scope.manage_appointments))):
    return _care_team(ctx)


@router.put("/care-team", response_model=CareTeam, summary="Set/change e.g. the Hausärztin (person's own choice)")
def set_care_team(body: SetCareTeamMember, ctx: Context = Depends(require(Scope.manage_appointments))):
    from app.services.appointments.service import providers

    if not any(p.id == body.provider_id for p in providers()):
        raise HTTPException(404, "Ordination/Einrichtung nicht gefunden")
    store.put("care_team_overrides", f"{ctx.subject.id}:{body.role}",
              {"role": body.role, "role_de": ROLE_DE.get(body.role, body.role), "provider_id": body.provider_id,
               "set_by_name": f"{ctx.actor.first_name} {ctx.actor.last_name}", "set_at": now_iso(),
               "since": now_iso()[:10]}, subject_id=ctx.subject.id)
    return _care_team(ctx)


__all__ = ["effective_scopes", "router"]
