"""Loads seed personas/delegations (YAML). Delegations can be modified at runtime (demo: revoke a scope)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from app.contracts.identity import Delegation, Person

HERE = Path(__file__).parent


@lru_cache
def _persons() -> dict[str, Person]:
    return {p["id"]: Person(**p) for p in yaml.safe_load((HERE / "personas.yaml").read_text(encoding="utf-8"))}


_DELEGATIONS: list[Delegation] | None = None


def _delegations() -> list[Delegation]:
    global _DELEGATIONS
    if _DELEGATIONS is None:
        _DELEGATIONS = [Delegation(**d) for d in yaml.safe_load((HERE / "delegations.yaml").read_text(encoding="utf-8"))]
    return _DELEGATIONS


def get_person(pid: str) -> Person | None:
    return _persons().get(pid)


def all_persons() -> list[Person]:
    return list(_persons().values())


def delegations_for(subject_id: str) -> list[Delegation]:
    return [d for d in _delegations() if d.grantor_id == subject_id]


def delegations_of_grantee(grantee_id: str) -> list[Delegation]:
    return [d for d in _delegations() if d.grantee_id == grantee_id]


def set_delegation_scopes(delegation_id: str, scopes: list) -> Delegation | None:
    for d in _delegations():
        if d.id == delegation_id:
            d.scopes = scopes
            return d
    return None


def reset_delegations() -> None:
    global _DELEGATIONS
    _DELEGATIONS = None
