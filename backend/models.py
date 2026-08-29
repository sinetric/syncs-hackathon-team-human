# Written by @sinetric & Claude, made with love <3 for SYNCS Hackathon 2026

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


class EventStatus(str, Enum):
    proposed = "proposed"
    approved = "approved"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class UrbanEvent(BaseModel):
    id: str                     # stable: f"{source}:{external_id}"
    type: EventType
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