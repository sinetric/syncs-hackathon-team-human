"""
Flat-file persistence layer.

Every reader/writer of on-disk state goes through here, so swapping to SQLite
or Postgres later is a one-file change.
"""

from __future__ import annotations

import json

from config import LOCATIONS_FILE, PLACES_FILE, PULSE_FILE, ROUTINES_FILE, SNAPSHOT_FILE
from models import Place, Routine, SavedLocation

# ---------------------------------------------------------------------------
# Saved locations
# ---------------------------------------------------------------------------


def load_locations() -> list[SavedLocation]:
    if not LOCATIONS_FILE.exists():
        return []
    return [SavedLocation(**item) for item in json.loads(LOCATIONS_FILE.read_text())]


def save_locations(locations: list[SavedLocation]) -> None:
    LOCATIONS_FILE.write_text(
        json.dumps([loc.model_dump(mode="json") for loc in locations], indent=2)
    )


def get_location(location_id: str) -> SavedLocation | None:
    return next((loc for loc in load_locations() if loc.id == location_id), None)


# ---------------------------------------------------------------------------
# Change-detection snapshot  (event id -> serialised UrbanEvent)
# ---------------------------------------------------------------------------


def load_snapshot() -> dict[str, dict]:
    if not SNAPSHOT_FILE.exists():
        return {}
    return json.loads(SNAPSHOT_FILE.read_text())


def save_snapshot(snapshot: dict[str, dict]) -> None:
    SNAPSHOT_FILE.write_text(json.dumps(snapshot, indent=2))


def clear_snapshot() -> None:
    """Demo helper: forget history so the next fetch reports events as 'new'."""
    SNAPSHOT_FILE.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Proactive "pulse"  (location id -> latest MonitorResult, as a dict)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# v1 contract: places + routines (docs/api-contract.md)
# ---------------------------------------------------------------------------


def load_places() -> list[Place]:
    if not PLACES_FILE.exists():
        return []
    return [Place(**item) for item in json.loads(PLACES_FILE.read_text())]


def save_places(places: list[Place]) -> None:
    PLACES_FILE.write_text(
        json.dumps([p.model_dump(mode="json") for p in places], indent=2)
    )


def get_place(place_id: str) -> Place | None:
    return next((p for p in load_places() if p.id == place_id), None)


def load_routines() -> list[Routine]:
    if not ROUTINES_FILE.exists():
        return []
    return [Routine(**item) for item in json.loads(ROUTINES_FILE.read_text())]


def save_routines(routines: list[Routine]) -> None:
    ROUTINES_FILE.write_text(
        json.dumps([r.model_dump(mode="json") for r in routines], indent=2)
    )


def get_routine(routine_id: str) -> Routine | None:
    return next((r for r in load_routines() if r.id == routine_id), None)


def load_pulse() -> dict[str, dict]:
    if not PULSE_FILE.exists():
        return {}
    return json.loads(PULSE_FILE.read_text())


def save_pulse(location_id: str, result: dict) -> None:
    pulse = load_pulse()
    pulse[location_id] = result
    PULSE_FILE.write_text(json.dumps(pulse, indent=2))
