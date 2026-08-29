"""
Pipeline orchestration.

    sources.fetch_all_events
        -> changes.detect_changes   (monitor mode)  |  all events (decision mode)
        -> geo.haversine_m          (relevance filter)
        -> impact.score_impact
        -> summary.summarise        (deterministic explanation + recommendation)
        -> llm.refine               (optional wording pass, USE_LLM=1)

Two modes:
  changes_only=True  (default, used by GET /monitor) — react to what *changed*
                     since the last snapshot. Persists the new snapshot.
  changes_only=False (used by POST /decision)        — evaluate *everything*
                     relevant near an address. Does not touch the snapshot.
"""

from __future__ import annotations

from config import RELEVANCE_RADIUS_M, USE_LLM
from geo import haversine_m
from models import ChangeType, DetectedChange, MonitorResult, SavedLocation
from pipeline.changes import detect_changes
from pipeline.impact import score_impact
from pipeline.summary import summarise
from sources import fetch_all_events


def run_pipeline_for_location(
    location: SavedLocation,
    question: str | None = None,
    changes_only: bool = True,
) -> MonitorResult:
    events = fetch_all_events()

    if changes_only:
        pairs = detect_changes(events)  # [(ChangeType, UrbanEvent)], persists snapshot
    else:
        pairs = [(ChangeType.existing, event) for event in events]

    detected: list[DetectedChange] = []
    for change_type, event in pairs:
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
        if changes_only:
            explanation = "No major changes detected near this location."
            recommendation = "No action needed right now. Know Ahead will keep monitoring."
        else:
            explanation = "No significant urban activity found near this address."
            recommendation = "Nothing nearby stands out. This address looks quiet for now."
    else:
        explanation, recommendation = summarise(location, detected)

    if question:
        explanation = f'You asked: “{question}”\n\n{explanation}'

    if USE_LLM and detected:
        from pipeline import llm

        explanation, recommendation = llm.refine(
            location, detected, explanation, recommendation, question=question
        )

    return MonitorResult(
        location=location,
        changes=detected,
        explanation=explanation,
        recommendation=recommendation,
    )
