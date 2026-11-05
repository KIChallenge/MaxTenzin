"""appointments — deterministic provider catalogue + synthetic slot generator + booking logic (no HTTP here).

Slots are DEMO slots: generated from weekday opening hours per provider kind, minus a stable pseudo-random
"already booked" mask (seeded by provider id + date, reproducible across runs) and minus real bookings.
"""

from __future__ import annotations

import random
import threading
import uuid
from datetime import date, datetime, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

from app.contracts.appointments import (
    Appointment,
    AppointmentStatus,
    Daypart,
    Provider,
    ProviderKind,
    Slot,
    SlotSearch,
)
from app.contracts.common import SourceKind, SourceRef
from app.core.db import now_iso, store
from app.core.knowledge import yaml_file

TZ = ZoneInfo("Europe/Vienna")
COLL = "appointments"
HORIZON_DAYS = 21               # search window from from_date
BOOKED_SHARE = 0.45             # share of generated slots that appear "already taken"
MAX_PER_PROVIDER = 2            # diversity: at most N slots per provider in one result list
BROCHURE = "ÖGK Serviceratgeber 2026"
DEMO_NOTICE = "Demo-Termin: wird nicht an eine echte Ordination übermittelt."

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# Opening hours per provider kind (weekday -> intervals). Providers may override via `hours` in providers.yaml.
KIND_HOURS: dict[ProviderKind, dict[str, list[str]]] = {
    ProviderKind.gp: {"mon": ["08:00-12:00"], "tue": ["14:00-18:00"], "wed": ["08:00-12:00"],
                      "thu": ["08:00-11:00", "15:00-18:00"], "fri": ["08:00-12:00"]},
    ProviderKind.specialist: {d: ["08:00-12:00", "13:00-16:00"] for d in ("mon", "tue", "wed", "thu")}
    | {"fri": ["08:00-12:00"]},
    ProviderKind.health_center: {d: ["07:30-12:00", "12:30-15:00"] for d in ("mon", "tue", "wed", "thu", "fri")},
    ProviderKind.counselling: {d: ["08:00-12:00"] for d in ("mon", "tue", "wed", "fri")}
    | {"thu": ["08:00-12:00", "13:00-15:30"]},
    ProviderKind.vaccination: {d: ["08:00-12:00"] for d in ("mon", "wed", "fri")}
    | {"tue": ["13:00-18:00"], "thu": ["13:00-18:00"]},
    ProviderKind.rehab: {d: ["08:00-12:00", "13:00-15:00"] for d in ("mon", "tue", "wed", "thu", "fri")},
}
KIND_SLOT_MINUTES: dict[ProviderKind, int] = {
    ProviderKind.gp: 20, ProviderKind.health_center: 20, ProviderKind.vaccination: 20,
    ProviderKind.specialist: 30, ProviderKind.counselling: 30, ProviderKind.rehab: 30,
}

# Topic aliases: words the agent / UI may use -> canonical topic tags in providers.yaml.
TOPIC_ALIASES = {
    "vu": "vorsorgeuntersuchung", "vorsorge": "vorsorgeuntersuchung",
    "darmkrebs": "darmkrebs_vorsorge", "darmspiegelung": "koloskopie",
    "grippe": "influenza", "grippeimpfung": "influenza", "influenza_impfung": "influenza",
    "arzttermin": "hausarzt", "hausaerztin": "hausarzt", "allgemeinmedizin": "hausarzt",
    "kontrolle": "hausarzt_kontrolle", "nachkontrolle": "hausarzt_kontrolle",
    "ernaehrung": "ernaehrungsberatung", "pflege_beratung": "pflegeberatung",
    "onkologie": "onkologie_nachsorge", "krebsnachsorge": "onkologie_nachsorge",
}

# Vienna districts: names + adjacency (shared borders incl. across the Danube/canal). Used only for ordering/hints.
DISTRICT_NAMES = {
    1: "Innere Stadt", 2: "Leopoldstadt", 3: "Landstraße", 4: "Wieden", 5: "Margareten", 6: "Mariahilf",
    7: "Neubau", 8: "Josefstadt", 9: "Alsergrund", 10: "Favoriten", 11: "Simmering", 12: "Meidling",
    13: "Hietzing", 14: "Penzing", 15: "Rudolfsheim-Fünfhaus", 16: "Ottakring", 17: "Hernals", 18: "Währing",
    19: "Döbling", 20: "Brigittenau", 21: "Floridsdorf", 22: "Donaustadt", 23: "Liesing",
}
NEIGHBOURS = {
    1: {2, 3, 4, 6, 7, 8, 9}, 2: {1, 3, 9, 11, 20, 22}, 3: {1, 2, 4, 10, 11}, 4: {1, 3, 5, 6, 10},
    5: {4, 6, 10, 12}, 6: {1, 4, 5, 7, 12, 15}, 7: {1, 6, 8, 15, 16}, 8: {1, 7, 9, 16, 17},
    9: {1, 2, 8, 17, 18, 19, 20}, 10: {3, 4, 5, 11, 12, 23}, 11: {2, 3, 10, 22}, 12: {5, 6, 10, 13, 14, 15, 23},
    13: {12, 14, 23}, 14: {12, 13, 15, 16, 17}, 15: {6, 7, 12, 14, 16}, 16: {7, 8, 14, 15, 17},
    17: {8, 9, 14, 16, 18}, 18: {9, 17, 19}, 19: {9, 18, 20, 21}, 20: {2, 9, 19, 21}, 21: {19, 20, 22},
    22: {2, 11, 21}, 23: {10, 12, 13},
}

_book_lock = threading.Lock()


# ----------------------------------------------------------------------------------------------- clock (injectable)
def now() -> datetime:
    """Current time in Vienna. Tests monkeypatch this function."""
    return datetime.now(TZ)


# ----------------------------------------------------------------------------------------------- providers
def _source(p: dict) -> SourceRef | None:
    if p.get("demo", True):
        return None
    page = int(p["page"])
    if p.get("form"):
        return SourceRef(kind=SourceKind.form, label=f"{p['form_label']}, S. {page}", ref=f"{p['form']}#page={page}")
    return SourceRef(kind=SourceKind.brochure, label=f"{BROCHURE}, S. {page}", ref=f"page:{page}")


@lru_cache
def _raw() -> tuple[dict, ...]:
    data = yaml_file("providers.yaml") or {}
    return tuple(data.get("providers", []))


@lru_cache
def providers() -> tuple[Provider, ...]:
    out = []
    for p in _raw():
        out.append(Provider(id=p["id"], name=p["name"], kind=ProviderKind(p["kind"]), specialty=p.get("specialty"),
                            topics=list(p.get("topics", [])), address=p["address"], zip=str(p["zip"]),
                            city=p.get("city", "Wien"), phone=p.get("phone", ""), contract=p.get("contract", "ÖGK"),
                            accessible=bool(p.get("accessible", True)), demo=bool(p.get("demo", True)),
                            source=_source(p)))
    return tuple(out)


def provider(pid: str) -> Provider | None:
    return next((p for p in providers() if p.id == pid), None)


@lru_cache
def _schedule(pid: str) -> tuple[dict[str, list[tuple[int, int]]], int]:
    """(weekday -> [(start_min, end_min)], slot length in minutes) for a provider."""
    raw = next(p for p in _raw() if p["id"] == pid)
    kind = ProviderKind(raw["kind"])
    hours = raw.get("hours") or KIND_HOURS[kind]
    parsed: dict[str, list[tuple[int, int]]] = {}
    for day, intervals in hours.items():
        parsed[day] = []
        for iv in intervals:
            a, b = iv.split("-")
            parsed[day].append((_minutes(a), _minutes(b)))
    return parsed, int(raw.get("slot_minutes") or KIND_SLOT_MINUTES[kind])


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def norm_topic(topic: str | None) -> str | None:
    if not topic:
        return None
    t = topic.strip().lower().replace("-", "_").replace(" ", "_")
    t = t.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return TOPIC_ALIASES.get(t, t)


def matches(p: Provider, topic: str | None = None, kind: ProviderKind | None = None,
            specialty: str | None = None, accessible_only: bool = False) -> bool:
    t = norm_topic(topic)
    if t and t not in p.topics and not (t == "hausarzt" and p.kind == ProviderKind.gp):
        return False
    if kind and p.kind != kind:
        return False
    if specialty and specialty.strip().lower() not in (p.specialty or "").lower():
        return False
    return not (accessible_only and not p.accessible)


# ----------------------------------------------------------------------------------------------- proximity
def district(zip_: str | None) -> int | None:
    if zip_ and len(zip_) == 4 and zip_.isdigit() and zip_[0] == "1":
        d = int(zip_[1:3])
        return d if d in DISTRICT_NAMES else None
    return None


def proximity(home_zip: str | None, p: Provider) -> tuple[int, int]:
    """(bucket, tie-break): 0 same district, 1 neighbouring district, 2 elsewhere in Vienna, 3 outside/unknown."""
    if home_zip and p.zip == home_zip:
        return (0, 0)
    hd, pd = district(home_zip), district(p.zip)
    if hd and pd:
        if hd == pd:
            return (0, 0)
        if pd in NEIGHBOURS[hd]:
            return (1, abs(hd - pd))
        return (2, abs(hd - pd))
    if home_zip and home_zip.isdigit() and p.zip.isdigit():
        return (3, abs(int(home_zip) - int(p.zip)))
    return (3, 9999)


def distance_hint(home_zip: str | None, p: Provider) -> str:
    pd = district(p.zip)
    where = f"{p.zip} {DISTRICT_NAMES[pd]}" if pd else f"{p.zip} {p.city}".strip()
    if not home_zip:
        return f"in {where}"
    bucket, _ = proximity(home_zip, p)
    return {
        0: f"im selben Bezirk ({p.zip})",
        1: f"im Nachbarbezirk ({where})",
        2: f"in einem anderen Bezirk ({where})",
    }.get(bucket, f"weiter entfernt ({where})")


# ----------------------------------------------------------------------------------------------- slot generator
def slot_id(pid: str, start: datetime) -> str:
    return f"{pid}@{start.isoformat(timespec='minutes')}"


def parse_slot_id(sid: str) -> tuple[str, datetime] | None:
    if "@" not in sid:
        return None
    pid, iso = sid.split("@", 1)
    try:
        start = datetime.fromisoformat(iso)
    except ValueError:
        return None
    if start.tzinfo is None:
        start = start.replace(tzinfo=TZ)
    return pid, start.astimezone(TZ)


def _taken_by_mask(pid: str, day: date, n: int) -> list[bool]:
    rng = random.Random(f"{pid}:{day.isoformat()}")  # str seed -> deterministic across runs/processes
    return [rng.random() < BOOKED_SHARE for _ in range(n)]


def day_slots(pid: str, day: date) -> list[tuple[datetime, datetime, bool]]:
    """All generated slots of a provider on one day as (start, end, taken_by_mask). Pure + reproducible."""
    hours, length = _schedule(pid)
    intervals = hours.get(WEEKDAYS[day.weekday()], [])
    starts: list[int] = []
    for a, b in intervals:
        m = a
        while m + length <= b:
            starts.append(m)
            m += length
    mask = _taken_by_mask(pid, day, len(starts))
    out = []
    for m, taken in zip(starts, mask, strict=True):
        start = datetime(day.year, day.month, day.day, m // 60, m % 60, tzinfo=TZ)
        out.append((start, start + timedelta(minutes=length), taken))
    return out


def booked_slot_ids() -> set[str]:
    return {a["slot"]["id"] for a in store.list(COLL) if a.get("status") == AppointmentStatus.booked.value}


def is_free(sid: str, at: datetime | None = None) -> tuple[Provider, datetime, datetime] | None:
    """Slot exists in the generator, is in the future, not masked and not booked -> (provider, start, end)."""
    parsed = parse_slot_id(sid)
    if not parsed:
        return None
    pid, start = parsed
    p = provider(pid)
    if p is None or start <= (at or now()):
        return None
    for s, e, taken in day_slots(pid, start.date()):
        if s == start:
            if taken or slot_id(pid, s) in booked_slot_ids():
                return None
            return p, s, e
    return None


def in_daypart(start: datetime, daypart: Daypart) -> bool:
    if daypart == Daypart.morning:
        return start.hour < 12
    if daypart == Daypart.afternoon:
        return start.hour >= 12
    return True


def search(q: SlotSearch, home_zip: str | None, at: datetime | None = None) -> list[Slot]:
    at = at or now()
    zip_ = q.zip or home_zip
    start_day = date.fromisoformat(q.from_date) if q.from_date else (at + timedelta(days=1)).date()
    cands = [p for p in providers() if matches(p, q.topic, q.kind, q.specialty, q.accessible_only)]
    taken = booked_slot_ids()
    limit = max(1, min(q.limit, 50))

    rows: list[tuple[tuple, Slot]] = []
    for p in cands:
        prox = proximity(zip_, p) if q.near else (0, 0)
        hint = distance_hint(zip_, p)
        found = 0
        for i in range(HORIZON_DAYS):
            day = start_day + timedelta(days=i)
            for s, e, masked in day_slots(p.id, day):
                sid = slot_id(p.id, s)
                if masked or sid in taken or s <= at or not in_daypart(s, q.daypart):
                    continue
                slot = Slot(id=sid, provider=p, start=s.isoformat(timespec="minutes"),
                            end=e.isoformat(timespec="minutes"), distance_hint_de=hint, demo=True)
                rows.append(((prox, s, p.id), slot))
                found += 1
                if found >= MAX_PER_PROVIDER:
                    break
            if found >= MAX_PER_PROVIDER:
                break
    rows.sort(key=lambda r: r[0])
    return [s for _, s in rows[:limit]]


def providers_near(topic: str | None, home_zip: str | None) -> list[Provider]:
    ps = [p for p in providers() if matches(p, topic)]
    return sorted(ps, key=lambda p: (proximity(home_zip, p), p.name))


# ----------------------------------------------------------------------------------------------- bring documents
def default_documents(p: Provider, step_topic: str | None, actor_is_subject: bool) -> list[str]:
    """Administrative checklist (what to bring). Never medical content."""
    docs = ["e-card"]
    t = norm_topic(step_topic)
    topics = set(p.topics) | ({t} if t else set())
    post_discharge = t in ("hausarzt_kontrolle", "reha", "reha_onko", "nachsorge", "onkologie_nachsorge") or \
        p.kind == ProviderKind.rehab
    if post_discharge:
        docs.append("Entlassungsbrief (Kopie)")
    if p.kind == ProviderKind.vaccination or (t and t in {"influenza", "covid19", "herpes_zoster", "pneumococcal",
                                                           "fsme", "dtp_polio", "impfung"}):
        docs.append("Impfpass (oder e-Impfpass am Handy)")
    if p.kind == ProviderKind.specialist:
        docs.append("Überweisung/Zuweisung (falls vorhanden)")
    if t in ("pflegegeld", "pflegeberatung") or (p.kind == ProviderKind.counselling and "pflegegeld" in topics
                                                  and not t):
        docs.append("Unterlagen zur Pflegesituation (z. B. Entlassungsbrief, Pflegegeldbescheid – falls vorhanden)")
    if not actor_is_subject:
        docs.append("Vollmacht bzw. Nachweis der Vertretung")
    return docs


def topic_from_step(step: dict) -> str | None:
    """Administrative topic of a Mein-Fall step: its benefit id, else keywords of the step title."""
    if step.get("benefit_id"):
        return step["benefit_id"]
    title = (step.get("title_de") or "").lower()
    if "kontrolle" in title and ("hausärzt" in title or "hausarzt" in title):
        return "hausarzt_kontrolle"
    if "reha" in title or "nachsorge" in title:
        return "reha"
    if "impf" in title:
        return "impfung"
    return None


def merge_documents(defaults: list[str], extra: list[str]) -> list[str]:
    out: list[str] = []
    for d in [*defaults, *extra]:
        d = d.strip()
        if d and d.lower() not in {x.lower() for x in out}:
            out.append(d)
    return out


# ----------------------------------------------------------------------------------------------- booking
def book(*, sid: str, subject_id: str, actor_id: str, purpose_de: str, docs: list[str],
         case_id: str | None, step_id: str | None) -> Appointment | None:
    """Atomically books a free slot. None -> slot not (or no longer) free."""
    with _book_lock:
        free = is_free(sid)
        if not free:
            return None
        p, s, e = free
        aid = f"apt-{uuid.uuid4().hex[:10]}"
        slot = Slot(id=sid, provider=p, start=s.isoformat(timespec="minutes"), end=e.isoformat(timespec="minutes"),
                    distance_hint_de="", demo=True)
        appt = Appointment(id=aid, subject_id=subject_id, booked_by=actor_id, slot=slot,
                           purpose_de=purpose_de.strip()[:300], bring_documents_de=docs, case_id=case_id,
                           step_id=step_id, created_at=now_iso(), ics_url=f"/api/appointments/{aid}/ics",
                           notice_de=DEMO_NOTICE)
        store.put(COLL, aid, appt.model_dump(mode="json"), subject_id=subject_id)
        return appt


def load(aid: str, subject_id: str) -> Appointment | None:
    d = store.get(COLL, aid)
    if not d or d.get("subject_id") != subject_id:
        return None
    return Appointment.model_validate(d)


def save(appt: Appointment) -> Appointment:
    store.put(COLL, appt.id, appt.model_dump(mode="json"), subject_id=appt.subject_id)
    return appt


def list_for(subject_id: str) -> list[Appointment]:
    items = [Appointment.model_validate(d) for d in store.list(COLL, subject_id=subject_id)]
    return sorted(items, key=lambda a: a.slot.start)


# ----------------------------------------------------------------------------------------------- iCalendar
_VTIMEZONE = [
    "BEGIN:VTIMEZONE", "TZID:Europe/Vienna",
    "BEGIN:DAYLIGHT", "TZOFFSETFROM:+0100", "TZOFFSETTO:+0200", "TZNAME:CEST", "DTSTART:19700329T020000",
    "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU", "END:DAYLIGHT",
    "BEGIN:STANDARD", "TZOFFSETFROM:+0200", "TZOFFSETTO:+0100", "TZNAME:CET", "DTSTART:19701025T030000",
    "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU", "END:STANDARD",
    "END:VTIMEZONE",
]


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r\n", "\\n") \
        .replace("\n", "\\n")


def _fold(line: str) -> str:
    """RFC 5545 line folding at 75 octets (UTF-8 safe)."""
    out, cur = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        if len(cur) + len(b) > (75 if not out else 74):
            out.append(cur.decode("utf-8"))
            cur = b""
        cur += b
    out.append(cur.decode("utf-8"))
    return "\r\n ".join(out)


def _local(iso: str) -> str:
    return datetime.fromisoformat(iso).astimezone(TZ).strftime("%Y%m%dT%H%M%S")


def ics(appt: Appointment) -> str:
    p = appt.slot.provider
    desc = [f"Anlass: {appt.purpose_de}"]
    if appt.bring_documents_de:
        desc.append("Mitbringen: " + ", ".join(appt.bring_documents_de))
    if p.phone:
        desc.append(f"Telefon: {p.phone}")
    desc.append(appt.notice_de)
    stamp = datetime.fromisoformat(appt.created_at).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//SV KI-Lotse//Termine//DE", "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH", *_VTIMEZONE,
        "BEGIN:VEVENT",
        f"UID:{appt.id}@sv-ki-lotse.local",
        f"DTSTAMP:{stamp}",
        f"DTSTART;TZID=Europe/Vienna:{_local(appt.slot.start)}",
        f"DTEND;TZID=Europe/Vienna:{_local(appt.slot.end)}",
        f"SUMMARY:{_esc('Termin: ' + p.name)}",
        f"LOCATION:{_esc(f'{p.name}, {p.address}, {p.zip} {p.city}')}",
        f"DESCRIPTION:{_esc(chr(10).join(desc))}",
        "STATUS:" + ("CANCELLED" if appt.status == AppointmentStatus.cancelled else "CONFIRMED"),
        "END:VEVENT", "END:VCALENDAR",
    ]
    return "\r\n".join(_fold(x) for x in lines) + "\r\n"
