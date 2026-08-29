"""
Flat-file persistence layer.

Every reader/writer of on-disk state goes through here, so swapping to SQLite
or Postgres later is a one-file change.
"""

from __future__ import annotations

import json

from config import LOCATIONS_FILE, PULSE_FILE, SNAPSHOT_FILE
from models import SavedLocation

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


def load_pulse() -> dict[str, dict]:
    if not PULSE_FILE.exists():
        return {}
    return json.loads(PULSE_FILE.read_text())


def save_pulse(location_id: str, result: dict) -> None:
    pulse = load_pulse()
    pulse[location_id] = result
    PULSE_FILE.write_text(json.dumps(pulse, indent=2))
