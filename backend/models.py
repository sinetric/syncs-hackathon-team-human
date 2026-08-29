# Written by @sinetric & Claude, made with love <3 for SYNCS Hackathon 2026

import uuid
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field

# Defining enums for common types

class EventType(str, Enum):
    development = "development"
    roadwork = "roadwork"
    infrastructure = "infrastructure"
    weather = "weather"
    flooding = "flooding"
    event = "event"
    obstruction = "obstruction"
    emergency = "emergency"

class SpecificEventType(str, Enum):
    concert = "concert"
    festival = "festival"
    market = "market"
    parade = "parade"
    gathering = "gathering"


class EventStatus(str, Enum):
    proposed = "proposed"
    approved = "approved"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class UrbanEvent(BaseModel):
    id: str                     # stable: f"{source}:{external_id}"
    type: EventType
    specific_type: SpecificEventType | None = None # only exists for EventType = EventType.event
    title: str
    description: str = ""
    latitude: float
    longitude: float
    start_date: date | None = None
    end_date: date | None = None
    source: str
    status: EventStatus = EventStatus.active
    last_updated: datetime
    raw: dict = Field(default_factory=dict, exclude=True)  # keep original for debugging

    def fingerprint(self) -> str: # unique identifier for the event based on its key fields
        """Fields whose change we consider a real change."""
        import hashlib, json
        keys = {
            "title": self.title, "status": self.status,
            "start": str(self.start_date), "end": str(self.end_date),
            "lat": round(self.latitude, 5), "lon": round(self.longitude, 5),
        }
        return hashlib.sha1(json.dumps(keys, sort_keys=True).encode()).hexdigest()


class Location(BaseModel):
    id: str
    label: str                  # "Home", "Work", ...
    address: str
    latitude: float
    longitude: float
    context: str = ""           # free text: "considering renewing a 12-month lease", "work from home"


class ChangeType(str, Enum):
    new = "new"
    updated = "updated"
    status_changed = "status_changed"
    date_changed = "date_changed"
    removed = "removed"
    existing = "existing"       # not a change — a relevant event already present (decision mode)


class Change(BaseModel):
    type: ChangeType
    event: UrbanEvent
    previous_fingerprint: str | None = None
    fields_changed: list[str] = []
    detected_at: datetime


class ImpactRating(str, Enum):
    none = "none"
    low = "low"
    medium = "medium"
    high = "high"


class ImpactReport(BaseModel): # we might be able to feed this into AI later
    event_id: str
    distance_m: float
    duration_days: int | None
    factors: dict[str, ImpactRating]   # {"noise": "high", "traffic": "medium", "dust": "medium"}
    overall: ImpactRating
    confidence: float           # 0..1 from evidence completeness
    evidence: list[str]         # deterministic bullet points feeding the LLM


# ---------------------------------------------------------------------------
# API / pipeline DTOs (used by main.py's MVP pipeline and FastAPI routes)
# ---------------------------------------------------------------------------


class SavedLocation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str                  # "home", "work", etc.
    address: str
    latitude: float
    longitude: float
    # user context that drives personalisation
    lease_end_date: date | None = None
    works_from_home: bool = False


class SavedLocationCreate(BaseModel):
    label: str
    address: str
    latitude: float
    longitude: float
    lease_end_date: date | None = None
    works_from_home: bool = False


class ImpactScore(BaseModel):
    noise: ImpactRating
    traffic: ImpactRating
    dust: ImpactRating
    duration_days: int | None = None


class DetectedChange(BaseModel):
    change_type: ChangeType
    event: UrbanEvent
    distance_m: float
    impact: ImpactScore


class MonitorResult(BaseModel):
    location: SavedLocation
    changes: list[DetectedChange]
    explanation: str
    recommendation: str


class DecisionRequest(BaseModel):
    address: str
    latitude: float
    longitude: float
    question: str               # e.g. "Should I renew my lease?"
    lease_end_date: date | None = None


# ---------------------------------------------------------------------------
# v1 contract models (docs/api-contract.md) — field-for-field with the doc.
# ---------------------------------------------------------------------------


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class Place(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("plc"))
    label: str
    address: str
    lat: float
    lng: float


class PlaceCreate(BaseModel):
    label: str = Field(min_length=1, max_length=60)
    address: str = Field(min_length=1, max_length=200)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class TravelMode(str, Enum):
    transit = "transit"
    drive = "drive"
    walk = "walk"


class Weekday(str, Enum):
    mon = "mon"
    tue = "tue"
    wed = "wed"
    thu = "thu"
    fri = "fri"
    sat = "sat"
    sun = "sun"


class Routine(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("rtn"))
    name: str
    origin_id: str
    dest_id: str
    days: list[Weekday]
    depart_local_time: str      # "HH:MM" local Australia/Sydney
    mode: TravelMode


class RoutineCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    origin_id: str
    dest_id: str
    days: list[Weekday] = Field(min_length=1)
    depart_local_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    mode: TravelMode


class AlertKind(str, Enum):
    transport_disruption = "transport_disruption"
    roadwork = "roadwork"
    incident = "incident"
    weather = "weather"
    construction = "construction"
    reminder = "reminder"
    advice = "advice"


class Severity(str, Enum):
    info = "info"
    watch = "watch"
    act = "act"


class AlertImpact(BaseModel):
    delay_minutes: int | None = None
    confidence: float


class AlertAffects(BaseModel):
    routine_ids: list[str] = []
    place_ids: list[str] = []
    leg_index: int | None = None


class AlertGeo(BaseModel):
    lat: float
    lng: float
    radius_m: int


class AlertAction(BaseModel):
    type: str                   # "leave_earlier" | "reroute" | ...
    label: str
    payload: dict = Field(default_factory=dict)


class AlertSource(BaseModel):
    name: str
    url: str | None = None
    fetched_at: datetime


class Alert(BaseModel):
    id: str
    kind: AlertKind
    severity: Severity
    title: str
    body: str
    impact: AlertImpact
    affects: AlertAffects
    valid_from: datetime
    valid_to: datetime
    geo: AlertGeo | None = None
    actions: list[AlertAction] = []
    source: AlertSource


class LegMode(str, Enum):
    walk = "walk"
    train = "train"
    bus = "bus"
    lightrail = "lightrail"
    ferry = "ferry"
    drive = "drive"


class JourneyLeg(BaseModel):
    index: int
    mode: LegMode
    from_: str = Field(alias="from")
    to: str
    depart_at: datetime
    arrive_at: datetime
    line: str | None = None
    duration_minutes: int

    model_config = {"populate_by_name": True}


class Fare(BaseModel):
    currency: str = "AUD"
    estimate_cents: int
    basis: str                  # e.g. "opal_adult_offpeak" — always an estimate


class ChecklistItem(BaseModel):
    id: str
    label: str
    reason: str


class TripMode(str, Enum):
    long = "long"               # > 60 minutes
    short = "short"


class JourneyPreview(BaseModel):
    duration_minutes: int
    trip_mode: TripMode
    legs: list[JourneyLeg]
    fare: Fare
    checklist: list[ChecklistItem]
    alerts: list[Alert]