from enum import StrEnum

from pydantic import BaseModel


class Scope(StrEnum):
    read_documents = "read_documents"
    prepare_applications = "prepare_applications"
    manage_appointments = "manage_appointments"
    view_health_prevention = "view_health_prevention"
    manage_case = "manage_case"


class Address(BaseModel):
    street: str
    house: str = ""
    zip: str
    city: str
    country: str = "Österreich"


class Person(BaseModel):
    id: str
    first_name: str
    last_name: str
    birth_date: str               # ISO date
    sex: str                      # "w" | "m" | "d"
    svnr: str                     # fictional
    insurer: str                  # e.g. "ÖGK"
    address: Address
    phone: str = ""
    email: str = ""
    marital_status: str = ""
    citizenship: str = "Österreich"
    language: str = "de"
    plain_language: bool = False


class Delegation(BaseModel):
    id: str
    grantor_id: str               # person who grants (e.g. Anna)
    grantee_id: str               # person who acts (e.g. Maria)
    scopes: list[Scope]
    relation: str = ""            # e.g. "Tochter"
    valid_until: str | None = None
    consent_note: str = ""


class Session(BaseModel):
    """Who is logged in (actor) and for whom they currently act (subject)."""
    token: str
    actor: Person
    subject: Person
    scopes: list[Scope]           # effective scopes for actor->subject (all scopes if actor == subject)
    delegations: list[Delegation] = []


class LoginRequest(BaseModel):
    persona_id: str               # mock ID Austria: pick a persona


class ActAsRequest(BaseModel):
    subject_id: str
