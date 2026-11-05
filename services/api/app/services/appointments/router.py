"""appointments — providers, slot search by preferences, booking (demo slots). (owner: WS-T).

Deterministic: providers from knowledge/providers.yaml, synthetic reproducible slots (service.py). Case steps are
updated via the cases HTTP API with the user's own token (scopes apply transitively), never via cases internals.
"""

from datetime import date

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from app.contracts.appointments import (
    Appointment,
    AppointmentStatus,
    BookingRequest,
    Provider,
    Slot,
    SlotSearch,
)
from app.contracts.identity import Scope
from app.core.auth import Context, require
from app.services.appointments import service

router = APIRouter(prefix="/api/appointments", tags=["appointments"])

RULE_SLOTS = "appointments.demo_slots.v1"


async def _call(request: Request, method: str, path: str, json: dict | None = None) -> httpx.Response:
    from app.main import app  # lazy: avoid import cycle

    headers = {k: v for k, v in request.headers.items() if k.lower() in ("authorization", "x-subject-id")}
    headers["X-Via"] = "service:appointments"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://internal") as c:
        return await c.request(method, path, headers=headers, json=json)


def _cite(ctx: Context, provs: list[Provider]) -> None:
    labels = sorted({p.source.label for p in provs if p.source})
    if labels:
        ctx.cite(*labels)
    ctx.rule_ids.append(RULE_SLOTS)


def _not_found() -> HTTPException:
    return HTTPException(404, "Termin nicht gefunden")


@router.get("/providers", response_model=list[Provider], summary="Providers by topic/kind/postcode")
def providers(topic: str | None = None, zip: str | None = None, ctx: Context = Depends(require())):
    res = service.providers_near(topic, zip or ctx.subject.address.zip)
    _cite(ctx, res)
    return res


@router.post("/slots/search", response_model=list[Slot], summary="Free slots matching preferences (near, daypart …)")
def search(body: SlotSearch, ctx: Context = Depends(require(Scope.manage_appointments))):
    if body.from_date:
        try:
            date.fromisoformat(body.from_date)
        except ValueError as e:
            raise HTTPException(422, "from_date bitte als Datum im Format JJJJ-MM-TT angeben.") from e
    slots = service.search(body, ctx.subject.address.zip)
    _cite(ctx, [s.provider for s in slots])
    return slots


@router.post("", response_model=Appointment, summary="Book a slot (demo) – links to Mein Fall")
async def book(body: BookingRequest, request: Request, ctx: Context = Depends(require(Scope.manage_appointments))):
    if not body.purpose_de.strip():
        raise HTTPException(422, "Bitte den Anlass in eigenen Worten angeben.")
    if body.step_id and not body.case_id:
        raise HTTPException(422, "step_id nur zusammen mit case_id angeben.")
    parsed = service.parse_slot_id(body.slot_id)
    prov = service.provider(parsed[0]) if parsed else None
    if prov is None:
        raise HTTPException(404, "Dieser Termin existiert nicht.")

    step_topic, step_open = None, False
    if body.case_id:  # validate the case link BEFORE booking (with the user's token -> manage_case applies)
        r = await _call(request, "GET", f"/api/cases/{body.case_id}")
        if r.status_code != 200:
            raise HTTPException(r.status_code, r.json().get("detail", "Fall nicht gefunden"))
        if body.step_id:
            step = next((s for s in r.json()["steps"] if s["id"] == body.step_id), None)
            if step is None:
                raise HTTPException(404, "Schritt nicht gefunden")
            step_topic, step_open = service.topic_from_step(step), step["status"] == "open"

    docs = service.merge_documents(
        service.default_documents(prov, step_topic, ctx.actor.id == ctx.subject.id), body.bring_documents_de)
    appt = service.book(sid=body.slot_id, subject_id=ctx.subject.id, actor_id=ctx.actor.id,
                        purpose_de=body.purpose_de, docs=docs, case_id=body.case_id, step_id=body.step_id)
    if appt is None:
        raise HTTPException(409, "Dieser Termin ist leider nicht mehr frei. Bitte einen anderen Termin wählen.")

    if body.case_id and body.step_id and step_open:
        await _call(request, "PATCH", f"/api/cases/{body.case_id}/steps/{body.step_id}", {"status": "in_progress"})
    _cite(ctx, [prov])
    return appt


@router.get("", response_model=list[Appointment], summary="Appointments of the current subject")
def list_appointments(ctx: Context = Depends(require(Scope.manage_appointments))):
    return service.list_for(ctx.subject.id)


@router.post("/{appointment_id}/cancel", response_model=Appointment, summary="Cancel an appointment")
def cancel(appointment_id: str, ctx: Context = Depends(require(Scope.manage_appointments))):
    appt = service.load(appointment_id, ctx.subject.id)
    if appt is None:
        raise _not_found()
    if appt.status != AppointmentStatus.cancelled:
        appt.status = AppointmentStatus.cancelled
        service.save(appt)
    return appt


@router.get("/{appointment_id}/ics", summary="Calendar file (.ics)")
def ics(appointment_id: str, ctx: Context = Depends(require(Scope.manage_appointments))):
    appt = service.load(appointment_id, ctx.subject.id)
    if appt is None:
        raise _not_found()
    return Response(content=service.ics(appt), media_type="text/calendar; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="termin-{appt.id}.ics"'})
