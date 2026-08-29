"""
Know Ahead — Backend MVP
=========================
Pipeline (per pitch doc, Section 9):

    Data sources -> Normalisation -> Geospatial filtering -> Change detection
        -> Impact model -> LLM -> Personalised explanation -> Recommendation/Alert

Design rule the whole file follows (Section 22):
    Code establishes the facts. AI explains their implications.
Distance, change detection, and impact *scoring* are deterministic Python.
The LLM only ever receives already-verified structured facts and turns them
into plain-English explanation + recommendation. It never invents distances,
dates, or event existence.

NOTE ON DATA SOURCE
The NSW Planning Portal's live "Online DA Data API" requires a subscription
key requested by email (not obtainable same-day). For the hackathon, the
`fetch_planning_events()` function below is a drop-in adapter: it returns
data shaped exactly like the real DA API's fields would map to our
UrbanEvent model, sourced from a local seed file. Swap its internals for a
real `requests.get(...)` call once you have a key — nothing else in the
pipeline needs to change.
"""

from __future__ import annotations

import json
import math
import os
import uuid
from datetime import date, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Config / storage paths (flat files are fine for a 24h MVP — swap for a real
# DB later without changing any function signature below)
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

LOCATIONS_FILE = DATA_DIR / "locations.json"
SNAPSHOT_FILE = DATA_DIR / "last_snapshot.json"  # for change detection
SEED_EVENTS_FILE = DATA_DIR / "seed_planning_events.json"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ---------------------------------------------------------------------------
# Models  (Section 10 — UrbanEvent normalised representation)
# ---------------------------------------------------------------------------


class EventType(str, Enum):
    DEVELOPMENT = "development"
    ROADWORK = "roadwork"
    WEATHER = "weather"
    EVENT = "event"


class ChangeType(str, Enum):
    NEW = "new_event"
    UPDATED = "updated_event"
    STATUS_CHANGED = "status_changed"
    CANCELLED = "cancelled"


class UrbanEvent(BaseModel):
    id: str
    type: EventType
    title: str
    description: str
    latitude: float
    longitude: float
    start_date: date
    end_date: Optional[date] = None
    source: str
    status: str
    last_updated: datetime


class SavedLocation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str  # "home", "work", etc.
    address: str
    latitude: float
    longitude: float
    # user context that drives personalisation (Section 14)
    lease_end_date: Optional[date] = None
    works_from_home: bool = False


class SavedLocationCreate(BaseModel):
    label: str
    address: str
    latitude: float
    longitude: float
    lease_end_date: Optional[date] = None
    works_from_home: bool = False


class ImpactRating(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ImpactScore(BaseModel):
    noise: ImpactRating
    traffic: ImpactRating
    dust: ImpactRating
    duration_days: Optional[int] = None


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
    question: str  # e.g. "Should I renew my lease?"
    lease_end_date: Optional[date] = None


# ---------------------------------------------------------------------------
# Step 1 — Collect data (adapter — swap internals for real API later)
# ---------------------------------------------------------------------------


def fetch_planning_events() -> list[UrbanEvent]:
    """
    Returns normalised UrbanEvents. Currently reads a local seed file shaped
    like real DA-API records. Replace the body of this function with a
    `requests.get(<real endpoint>, headers={"Ocp-Apim-Subscription-Key": ...})`
    call once a key is issued — the return type contract stays identical.
    """
    if not SEED_EVENTS_FILE.exists():
        _write_default_seed()

    raw = json.loads(SEED_EVENTS_FILE.read_text())
    return [UrbanEvent(**item) for item in raw]


def _write_default_seed() -> None:
    """One realistic seed event ~180m from a plausible Sydney home address,
    matching the pitch doc's headline demo scenario (Section 32)."""
    seed = [
        {
            "id": "DA-2026-00042",
            "type": "development",
            "title": "Mixed-use residential development — 8 storeys",
            "description": (
                "Demolition of existing structure and construction of an "
                "8-storey mixed-use building with basement parking."
            ),
            "latitude": -33.8845,
            "longitude": 151.2005,
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=18 * 30)),
            "source": "nsw_planning_portal_seed",
            "status": "approved",
            "last_updated": datetime.now().isoformat(),
        }
    ]
    SEED_EVENTS_FILE.write_text(json.dumps(seed, indent=2))


# ---------------------------------------------------------------------------
# Step 2 — Change detection (Section 11)
# ---------------------------------------------------------------------------


def _load_snapshot() -> dict[str, dict]:
    if not SNAPSHOT_FILE.exists():
        return {}
    return json.loads(SNAPSHOT_FILE.read_text())


def _save_snapshot(events: list[UrbanEvent]) -> None:
    snapshot = {e.id: e.model_dump(mode="json") for e in events}
    SNAPSHOT_FILE.write_text(json.dumps(snapshot, indent=2))


def detect_changes(current_events: list[UrbanEvent]) -> list[tuple[ChangeType, UrbanEvent]]:
    previous = _load_snapshot()
    changes: list[tuple[ChangeType, UrbanEvent]] = []

    for event in current_events:
        prev = previous.get(event.id)
        if prev is None:
            changes.append((ChangeType.NEW, event))
        elif prev.get("status") != event.status:
            changes.append((ChangeType.STATUS_CHANGED, event))
        elif prev.get("end_date") != str(event.end_date):
            changes.append((ChangeType.UPDATED, event))

    _save_snapshot(current_events)
    return changes


def reset_snapshot() -> None:
    """Useful for demoing: clears history so the next fetch shows as 'new'."""
    if SNAPSHOT_FILE.exists():
        SNAPSHOT_FILE.unlink()


# ---------------------------------------------------------------------------
# Step 3 — Geospatial filtering (Section 12) — pure math, no AI
# ---------------------------------------------------------------------------

EARTH_RADIUS_M = 6371000


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


RELEVANCE_RADIUS_M = 1000  # events beyond this are ignored for a location


# ---------------------------------------------------------------------------
# Step 4 — Impact scoring (Section 13) — deterministic rules, not ML
# ---------------------------------------------------------------------------


def score_impact(event: UrbanEvent, distance_m: float) -> ImpactScore:
    duration_days = None
    if event.end_date:
        duration_days = (event.end_date - event.start_date).days

    def band(near_high: float, near_medium: float) -> ImpactRating:
        if distance_m <= near_high:
            return ImpactRating.HIGH
        if distance_m <= near_medium:
            return ImpactRating.MEDIUM
        return ImpactRating.LOW

    if event.type == EventType.DEVELOPMENT:
        return ImpactScore(
            noise=band(250, 600),
            traffic=band(400, 800),
            dust=band(250, 600),
            duration_days=duration_days,
        )
    if event.type == EventType.ROADWORK:
        return ImpactScore(
            noise=band(150, 400),
            traffic=band(600, 1000),
            dust=band(150, 400),
            duration_days=duration_days,
        )
    if event.type == EventType.WEATHER:
        return ImpactScore(
            noise=ImpactRating.LOW,
            traffic=band(500, 1000),
            dust=ImpactRating.LOW,
            duration_days=duration_days,
        )
    # EVENT type (concerts, festivals, etc.)
    return ImpactScore(
        noise=band(300, 700),
        traffic=band(500, 1000),
        dust=ImpactRating.LOW,
        duration_days=duration_days,
    )


# ---------------------------------------------------------------------------
# Step 5 — LLM interpretation layer (Section 21)
# Structured facts in -> explanation + recommendation out. Never the reverse.
# ---------------------------------------------------------------------------


def build_llm_prompt(location: SavedLocation, changes: list[DetectedChange], question: Optional[str] = None) -> str:
    facts = []
    for c in changes:
        facts.append(
            f"- {c.event.title} ({c.event.type.value}), {c.distance_m:.0f}m from "
            f"{location.label}. Status: {c.event.status}. "
            f"Duration: {c.impact.duration_days or 'unknown'} days. "
            f"Impact — noise: {c.impact.noise.value}, traffic: {c.impact.traffic.value}, "
            f"dust: {c.impact.dust.value}."
        )
    context_lines = [f"Verified signals near {location.label} ({location.address}):", *facts]

    if location.lease_end_date:
        context_lines.append(f"User's lease ends: {location.lease_end_date}.")
    if location.works_from_home:
        context_lines.append("User works from home.")
    if question:
        context_lines.append(f"User's question: \"{question}\"")

    context_lines.append(
        "\nUsing ONLY the facts above, write: (1) a short explanation of what "
        "changed and why it matters, (2) a clear, appropriately cautious "
        "recommendation of what to consider doing. Do not invent facts not "
        "listed above. Distinguish known facts from inferred/predicted ones."
    )
    return "\n".join(context_lines)


def call_llm(prompt: str) -> str:
    """Calls Claude with the verified-facts prompt. Falls back to a
    deterministic template if no API key is set, so the pipeline still
    runs end-to-end without network access during dev."""
    if not ANTHROPIC_API_KEY:
        return _fallback_explanation(prompt)

    import anthropic  # pip install anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def _fallback_explanation(prompt: str) -> str:
    return (
        "[LLM not configured — set ANTHROPIC_API_KEY] Based on the verified "
        "signals above, review the nearest high-impact event and consider "
        "how its duration overlaps with your plans before deciding."
    )


# ---------------------------------------------------------------------------
# Pipeline orchestration
# ---------------------------------------------------------------------------


def run_pipeline_for_location(location: SavedLocation, question: Optional[str] = None) -> MonitorResult:
    all_events = fetch_planning_events()
    changed = detect_changes(all_events)

    detected: list[DetectedChange] = []
    for change_type, event in changed:
        distance = haversine_distance_m(
            location.latitude, location.longitude, event.latitude, event.longitude
        )
        if distance > RELEVANCE_RADIUS_M:
            continue
        impact = score_impact(event, distance)
        detected.append(
            DetectedChange(change_type=change_type, event=event, distance_m=distance, impact=impact)
        )

    if not detected:
        return MonitorResult(
            location=location,
            changes=[],
            explanation="No major changes detected near this location.",
            recommendation="No action needed right now.",
        )

    prompt = build_llm_prompt(location, detected, question=question)
    llm_output = call_llm(prompt)

    # naive split; fine for hackathon demo — refine prompt for structured output if time allows
    return MonitorResult(
        location=location,
        changes=detected,
        explanation=llm_output,
        recommendation=llm_output,
    )


# ---------------------------------------------------------------------------
# Persistence helpers for saved locations
# ---------------------------------------------------------------------------


def _load_locations() -> list[SavedLocation]:
    if not LOCATIONS_FILE.exists():
        return []
    raw = json.loads(LOCATIONS_FILE.read_text())
    return [SavedLocation(**item) for item in raw]


def _save_locations(locations: list[SavedLocation]) -> None:
    LOCATIONS_FILE.write_text(json.dumps([l.model_dump(mode="json") for l in locations], indent=2))


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="Know Ahead API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for prod; fine for a hackathon demo
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/locations", response_model=SavedLocation)
def create_location(payload: SavedLocationCreate):
    locations = _load_locations()
    new_location = SavedLocation(**payload.model_dump())
    locations.append(new_location)
    _save_locations(locations)
    return new_location


@app.get("/locations", response_model=list[SavedLocation])
def list_locations():
    return _load_locations()


@app.get("/monitor/{location_id}", response_model=MonitorResult)
def monitor_location(location_id: str):
    locations = _load_locations()
    match = next((l for l in locations if l.id == location_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Location not found")
    return run_pipeline_for_location(match)


@app.post("/decision", response_model=MonitorResult)
def decision_mode(payload: DecisionRequest):
    """Section 6 — 'Before You Commit' decision support. Doesn't require a
    saved location; takes an ad-hoc address + question."""
    ad_hoc_location = SavedLocation(
        label="this address",
        address=payload.address,
        latitude=payload.latitude,
        longitude=payload.longitude,
        lease_end_date=payload.lease_end_date,
    )
    return run_pipeline_for_location(ad_hoc_location, question=payload.question)


@app.post("/demo/reset")
def demo_reset():
    """Clears change-detection history so the next /monitor call shows the
    seed event as 'new' — use this right before your demo run."""
    reset_snapshot()
    return {"status": "snapshot cleared"}


@app.get("/health")
def health():
    return {"status": "ok"}
