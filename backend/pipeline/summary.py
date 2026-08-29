"""
Deterministic explanation + recommendation.

This replaces the LLM interpretation layer: every sentence is derived from
already-verified structured facts (event, distance, duration, user context).
No model calls, nothing invented. A natural-language layer can later wrap this
function without changing the pipeline or the API contract.
"""

from __future__ import annotations

from datetime import date

from models import DetectedChange, EventType, ImpactRating, SavedLocation
from pipeline.impact import overall_rating, rank

_CHANGE_LABEL = {
    "new": "New",
    "updated": "Updated",
    "status_changed": "Status change on",
    "date_changed": "Rescheduled",
    "removed": "Removed",
}


def _duration_phrase(days: int | None) -> str:
    if not days:
        return "an unknown period"
    if days < 45:
        return f"~{days} days"
    return f"~{round(days / 30)} months"


def summarise(location: SavedLocation, detected: list[DetectedChange]) -> tuple[str, str]:
    """Return (explanation, recommendation) for the most significant change."""
    lead = max(
        detected,
        key=lambda d: (rank(overall_rating(d.impact)), -d.distance_m),
    )
    ev, imp = lead.event, lead.impact
    dist = round(lead.distance_m)
    label = _CHANGE_LABEL.get(lead.change_type.value, "Detected")

    explanation = (
        f"{label} {ev.type.value} detected {dist} m from {location.label}: "
        f"“{ev.title}”. Expected to run {_duration_phrase(imp.duration_days)}. "
        f"Potential impact — noise: {imp.noise.value}, "
        f"traffic: {imp.traffic.value}, dust: {imp.dust.value}."
    )
    if len(detected) > 1:
        explanation += f" ({len(detected) - 1} other change(s) nearby.)"

    return explanation, _recommend(location, lead)


def _recommend(location: SavedLocation, change: DetectedChange) -> str:
    ev, imp = change.event, change.impact

    lease_overlap = (
        location.lease_end_date is not None
        and ev.end_date is not None
        and date.today() <= location.lease_end_date <= ev.end_date
    )

    if ev.type == EventType.development and lease_overlap:
        return (
            f"This construction is likely to overlap your lease ending "
            f"{location.lease_end_date}. Investigate permitted construction hours "
            f"and expected noise before renewing."
        )
    if location.works_from_home and imp.noise == ImpactRating.high:
        return (
            "You work from home and the noise impact is high. Check the site's "
            "permitted working hours and plan focus time around them."
        )
    if ev.type == EventType.roadwork and imp.traffic in (ImpactRating.high, ImpactRating.medium):
        return (
            "This may disrupt nearby roads and your usual routes. Check for "
            "alternatives and allow extra travel time while works are active."
        )
    if ImpactRating.high in (imp.noise, imp.traffic, imp.dust):
        return (
            "A high potential impact was detected nearby. Review the event "
            "details and monitor it for status or schedule changes."
        )
    return "Low potential impact for now. Know Ahead will keep monitoring for changes."
