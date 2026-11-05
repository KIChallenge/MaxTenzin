"""Mock ID Austria + delegation (Vertretung) + scope enforcement.

Stateless: token = "demo-<persona_id>" identifies the ACTOR; header X-Subject-Id selects the person acted for.
Effective scopes = all scopes if actor == subject, else the scopes of a valid delegation grantor->actor.
The AI agent sends the user's own token -> it can never do more than the user (no special rights).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import Depends, Header, HTTPException, Request

from app.contracts.identity import Person, Scope
from app.seed.loader import delegations_for, get_person

TOKEN_PREFIX = "demo-"


@dataclass
class Context:
    actor: Person
    subject: Person
    scopes: set[Scope]
    via: str = "ui"
    tool: str | None = None
    sources: list[str] = field(default_factory=list)
    rule_ids: list[str] = field(default_factory=list)

    def cite(self, *labels: str) -> None:
        self.sources.extend(labels)


def effective_scopes(actor_id: str, subject_id: str) -> set[Scope]:
    if actor_id == subject_id:
        return set(Scope)
    scopes: set[Scope] = set()
    for d in delegations_for(subject_id):
        if d.grantee_id == actor_id:
            scopes |= set(d.scopes)
    return scopes


def get_context(
    request: Request,
    authorization: str = Header("", alias="Authorization"),
    x_subject_id: str | None = Header(None, alias="X-Subject-Id"),
    x_via: str = Header("ui", alias="X-Via"),
    x_agent_tool: str | None = Header(None, alias="X-Agent-Tool"),
) -> Context:
    token = authorization.removeprefix("Bearer ").strip()
    if not token.startswith(TOKEN_PREFIX):
        raise HTTPException(401, "Nicht angemeldet (ID Austria Demo-Login erforderlich).")
    actor = get_person(token.removeprefix(TOKEN_PREFIX))
    if actor is None:
        raise HTTPException(401, "Unbekannte Person.")
    subject = get_person(x_subject_id) if x_subject_id else actor
    if subject is None:
        raise HTTPException(404, "Person nicht gefunden.")
    scopes = effective_scopes(actor.id, subject.id)
    if not scopes:
        raise HTTPException(403, f"Keine Vertretungsbefugnis für {subject.first_name} {subject.last_name}.")
    ctx = Context(actor=actor, subject=subject, scopes=scopes, via=x_via, tool=x_agent_tool)
    request.state.ctx = ctx
    return ctx


def require(scope: Scope | None = None):
    """Dependency factory: authenticated context + optional scope check (recorded in audit)."""

    def dep(request: Request, ctx: Context = Depends(get_context)) -> Context:
        request.state.scope_required = scope.value if scope else None
        if scope and scope not in ctx.scopes:
            request.state.allowed = False
            raise HTTPException(
                403,
                f"Fehlende Berechtigung '{scope.value}' für {ctx.subject.first_name} {ctx.subject.last_name}.",
            )
        return ctx

    return dep
