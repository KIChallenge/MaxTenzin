"""Lebenslage: the person's current care situation as overlapping episodes (hospital, rehab, therapy, home care …).

Episodes are set by the person/representative, or SUGGESTED from documents and only applied after explicit consent.
Changes drive deterministic effects: reminders (Meldepflichten), eligibility facts, form prefill, case steps.
"""

from enum import StrEnum

from pydantic import BaseModel, Field

from app.contracts.common import SourceRef


class EpisodeType(StrEnum):
    hospital = "hospital"                  # Krankenhausaufenthalt (stationär)
    rehab_inpatient = "rehab_inpatient"    # Reha stationär
    rehab_outpatient = "rehab_outpatient"  # Reha ambulant
    therapy = "therapy"                    # laufende Therapie (subtype: strahlentherapie, chemotherapie, physiotherapie, dialyse, sonstige)
    home_care = "home_care"                # zu Hause mit Unterstützung (mobile Dienste, Angehörige)
    nursing_home = "nursing_home"          # Pflegeheim (dauerhaft/Kurzzeit)
    sick_leave = "sick_leave"              # Krankenstand
    cure = "cure"                          # Kur / Gesundheitsvorsorge Aktiv


class EpisodeStatus(StrEnum):
    suggested = "suggested"    # from a document – NOT applied until the person confirms
    planned = "planned"        # confirmed, starts in the future
    active = "active"          # confirmed, ongoing
    ended = "ended"            # confirmed, finished
    rejected = "rejected"      # suggestion declined by the person


class Episode(BaseModel):
    id: str
    subject_id: str
    type: EpisodeType
    subtype: str | None = None             # e.g. strahlentherapie
    title_de: str                          # e.g. "Krankenhausaufenthalt", "Ambulante Strahlentherapie"
    start: str | None = None               # ISO date (None = unknown)
    end: str | None = None                 # ISO date (None = ongoing/unknown)
    end_estimate_de: str | None = None     # e.g. "Mitte November 2026" when only vague
    institution: str | None = None
    status: EpisodeStatus
    source: SourceRef                      # document quote+page, or "Angabe von Maria Berger"
    created_by: str                        # actor id
    confirmed_by: str | None = None        # actor id who consented (suggestions)
    confirmed_at: str | None = None
    note_de: str | None = None


class EpisodeCreate(BaseModel):
    type: EpisodeType
    subtype: str | None = None
    title_de: str | None = None
    start: str | None = None
    end: str | None = None
    end_estimate_de: str | None = None
    institution: str | None = None
    note_de: str | None = None


class EpisodeUpdate(BaseModel):
    start: str | None = None
    end: str | None = None
    end_estimate_de: str | None = None
    institution: str | None = None
    note_de: str | None = None
    status: EpisodeStatus | None = None    # e.g. ended


class EffectKind(StrEnum):
    reminder = "reminder"      # Meldepflicht / Frist (also shown in the inbox)
    fact = "fact"              # fact passed to eligibility (e.g. treatment_type=strahlentherapie)
    prefill = "prefill"        # form fields that can be prefilled from the situation
    case_step = "case_step"    # suggested/created step in Mein Fall
    hint = "hint"              # other consequence (e.g. Pflegegeld ruht während Spitalsaufenthalt)


class Effect(BaseModel):
    kind: EffectKind
    episode_id: str | None = None
    title_de: str
    detail_de: str = ""
    due_date: str | None = None
    key: str | None = None                 # fact key / form field / benefit id
    value: str | bool | float | None = None
    source: SourceRef | None = None


class SituationOverview(BaseModel):
    subject_id: str
    as_of: str
    current: list[Episode] = []            # active (incl. ongoing without end)
    upcoming: list[Episode] = []           # planned
    past: list[Episode] = []               # ended
    suggestions: list[Episode] = []        # from documents, awaiting consent
    effects: list[Effect] = []
    facts: dict = Field({}, description="Eligibility facts derived from confirmed episodes")
    summary_de: str = ""                   # one-line plain summary, e.g. "Zu Hause mit Unterstützung, laufende Strahlentherapie"
