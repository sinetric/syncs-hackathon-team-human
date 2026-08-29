"""
Change detection (pitch Section 11).

Deterministic diff of the current fetch against the last stored snapshot:
what turns Know Ahead from an aggregator into a monitoring system.
"""

from __future__ import annotations

from models import ChangeType, UrbanEvent
from store import load_snapshot, save_snapshot


def _iso_or_none(value) -> str | None:
    return str(value) if value is not None else None


def detect_changes(current_events: list[UrbanEvent]) -> list[tuple[ChangeType, UrbanEvent]]:
    """Compare `current_events` with the previous snapshot, then persist the new
    snapshot. Returns (change_type, event) for every event that changed."""
    previous = load_snapshot()
    changes: list[tuple[ChangeType, UrbanEvent]] = []

    for event in current_events:
        prev = previous.get(event.id)
        if prev is None:
            changes.append((ChangeType.new, event))
        elif prev.get("status") != event.status:
            changes.append((ChangeType.status_changed, event))
        elif prev.get("end_date") != _iso_or_none(event.end_date):
            changes.append((ChangeType.date_changed, event))

    save_snapshot({e.id: e.model_dump(mode="json") for e in current_events})
    return changes
