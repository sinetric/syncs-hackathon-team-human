"""
Pipeline orchestration.

    sources.fetch_all_events
        -> changes.detect_changes
        -> geo.haversine_m  (relevance filter)
        -> impact.score_impact
        -> summary.summarise (deterministic explanation + recommendation)
"""

from __future__ import annotations

from config import RELEVANCE_RADIUS_M
from geo import haversine_m
from models import DetectedChange, MonitorResult, SavedLocation
from pipeline.changes import detect_changes
from pipeline.impact import score_impact
from pipeline.summary import summarise
from sources import fetch_all_events


def run_pipeline_for_location(location: SavedLocation) -> MonitorResult:
    events = fetch_all_events()
    changed = detect_changes(events)

    detected: list[DetectedChange] = []
    for change_type, event in changed:
        distance_m = haversine_m(
            location.latitude, location.longitude, event.latitude, event.longitude
        )
        if distance_m > RELEVANCE_RADIUS_M:
            continue
        detected.append(
            DetectedChange(
                change_type=change_type,
                event=event,
                distance_m=distance_m,
                impact=score_impact(event, distance_m),
            )
        )

    if not detected:
        return MonitorResult(
            location=location,
            changes=[],
            explanation="No major changes detected near this location.",
            recommendation="No action needed right now. Know Ahead will keep monitoring.",
        )

    explanation, recommendation = summarise(location, detected)
    return MonitorResult(
        location=location,
        changes=detected,
        explanation=explanation,
        recommendation=recommendation,
    )
