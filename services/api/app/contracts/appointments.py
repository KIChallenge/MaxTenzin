"""Appointments: find providers, search slots by preferences, prepare and book (demo slots, clearly labelled)."""

from enum import StrEnum

from pydantic import BaseModel, Field

from app.contracts.common import SourceRef


class ProviderKind(StrEnum):
    gp = "gp"                         # Allgemeinmedizin (Kassenvertrag)
    specialist = "specialist"         # Fachärztin/-arzt (specialty set)
    health_center = "health_center"   # ÖGK Gesundheitszentrum / Ambulatorium
    counselling = "counselling"       # Beratung: PVA, FSW Beratungszentrum Pflege, ÖGK Kundenservice
    vaccination = "vaccination"       # Impfstelle
    rehab = "rehab"                   # Reha-/Nachsorge-Einrichtung


class Provider(BaseModel):
    id: str
    name: str
    kind: ProviderKind
    specialty: str | None = None      # e.g. "Gastroenterologie", "Onkologie", "Pflegeberatung"
    topics: list[str] = []            # benefit/prevention ids it serves (e.g. pflegegeld, vorsorgeuntersuchung)
    address: str
    zip: str
    city: str = "Wien"
    phone: str = ""
    contract: str = "ÖGK"             # Kassenvertrag / Träger
    accessible: bool = True           # barrierefrei
    demo: bool = True                 # synthetic demo provider (not a real practice)
    source: SourceRef | None = None   # for real facilities (e.g. Serviceratgeber page)


class Daypart(StrEnum):
    morning = "morning"               # vormittags (< 12:00)
    afternoon = "afternoon"           # nachmittags (>= 12:00)
    any = "any"


class SlotSearch(BaseModel):
    topic: str | None = None          # what for: e.g. "vorsorgeuntersuchung", "pflegeberatung", "hausarzt_kontrolle"
    kind: ProviderKind | None = None
    specialty: str | None = None
    zip: str | None = None            # default: subject's address
    near: bool = True                 # prefer same/neighbouring district
    daypart: Daypart = Daypart.any
    from_date: str | None = None      # ISO date, default tomorrow
    accessible_only: bool = False
    limit: int = 6


class Slot(BaseModel):
    id: str                           # stable id: "<provider_id>@<iso start>"
    provider: Provider
    start: str                        # ISO datetime (Europe/Vienna)
    end: str
    distance_hint_de: str = ""        # e.g. "im selben Bezirk (1030)"
    demo: bool = True


class AppointmentStatus(StrEnum):
    booked = "booked"
    cancelled = "cancelled"


class BookingRequest(BaseModel):
    slot_id: str
    purpose_de: str = Field(..., description="Anlass in eigenen Worten (kein medizinischer Befund)")
    case_id: str | None = None        # link to Mein Fall
    step_id: str | None = None
    bring_documents_de: list[str] = []  # what to bring (e.g. e-card, Entlassungsbrief)


class Appointment(BaseModel):
    id: str
    subject_id: str
    booked_by: str                    # actor id (e.g. Maria for Anna)
    slot: Slot
    purpose_de: str
    status: AppointmentStatus = AppointmentStatus.booked
    bring_documents_de: list[str] = []
    case_id: str | None = None
    step_id: str | None = None
    created_at: str
    ics_url: str                      # GET → calendar file
    notice_de: str = "Demo-Termin: wird nicht an eine echte Ordination übermittelt."
