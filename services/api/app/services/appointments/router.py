"""appointments — providers, slot search by preferences, booking (demo slots). STUB (owner: WS-T)."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.contracts.appointments import Appointment, BookingRequest, Provider, Slot, SlotSearch
from app.contracts.identity import Scope
from app.core.auth import Context, require

router = APIRouter(prefix="/api/appointments", tags=["appointments"])


@router.get("/providers", response_model=list[Provider], summary="Providers by topic/kind/postcode")
def providers(topic: str | None = None, zip: str | None = None, ctx: Context = Depends(require())):
    return []  # STUB


@router.post("/slots/search", response_model=list[Slot], summary="Free slots matching preferences (near, daypart …)")
def search(body: SlotSearch, ctx: Context = Depends(require(Scope.manage_appointments))):
    return []  # STUB


@router.post("", response_model=Appointment, summary="Book a slot (demo) – links to Mein Fall")
def book(body: BookingRequest, ctx: Context = Depends(require(Scope.manage_appointments))):
    raise HTTPException(501, "Terminbuchung noch nicht verfügbar")  # STUB


@router.get("", response_model=list[Appointment], summary="Appointments of the current subject")
def list_appointments(ctx: Context = Depends(require(Scope.manage_appointments))):
    return []  # STUB


@router.post("/{appointment_id}/cancel", response_model=Appointment, summary="Cancel an appointment")
def cancel(appointment_id: str, ctx: Context = Depends(require(Scope.manage_appointments))):
    raise HTTPException(404, "Termin nicht gefunden")  # STUB


@router.get("/{appointment_id}/ics", summary="Calendar file (.ics)")
def ics(appointment_id: str, ctx: Context = Depends(require(Scope.manage_appointments))):
    return Response(status_code=404)  # STUB
