"""
Impact scoring (pitch Section 13).

Deterministic distance-banded rules per event type — not ML. The output feeds
the (equally deterministic) summary layer and the API response.
"""

from __future__ import annotations

from models import EventType, ImpactRating, ImpactScore, UrbanEvent

_ORDER = [ImpactRating.none, ImpactRating.low, ImpactRating.medium, ImpactRating.high]


def rank(rating: ImpactRating) -> int:
    """Sortable severity: none < low < medium < high."""
    return _ORDER.index(rating)


def overall_rating(impact: ImpactScore) -> ImpactRating:
    return max((impact.noise, impact.traffic, impact.dust), key=rank)


def score_impact(event: UrbanEvent, distance_m: float) -> ImpactScore:
    duration_days = None
    if event.start_date and event.end_date:
        duration_days = (event.end_date - event.start_date).days

    def band(near_high: float, near_medium: float) -> ImpactRating:
        if distance_m <= near_high:
            return ImpactRating.high
        if distance_m <= near_medium:
            return ImpactRating.medium
        return ImpactRating.low

    if event.type == EventType.development:
        return ImpactScore(
            noise=band(250, 600),
            traffic=band(400, 800),
            dust=band(250, 600),
            duration_days=duration_days,
        )
    if event.type == EventType.roadwork:
        return ImpactScore(
            noise=band(150, 400),
            traffic=band(600, 1000),
            dust=band(150, 400),
            duration_days=duration_days,
        )
    if event.type == EventType.weather:
        return ImpactScore(
            noise=ImpactRating.low,
            traffic=band(500, 1000),
            dust=ImpactRating.low,
            duration_days=duration_days,
        )
    if event.type == EventType.event:
        specific = event.specific_type

        traffic = {
            "concert": band(400, 800),
            "festival": band(400, 800),
            "market": band(400, 800),
            "parade": band(400, 800),
            "gathering": band(400, 800),
        }

        dustImpactRating = {
            "concert": ImpactRating.low,
            "festival": ImpactRating.medium,
            "market": ImpactRating.low,
            "parade": ImpactRating.low,
            "gathering": ImpactRating.low,
        }

        return ImpactScore(
            noise=ImpactRating.high,
            traffic=traffic.get(specific, band(400, 800)),
            dust=dustImpactRating.get(specific, ImpactRating.low),
            duration_days=duration_days,
        )
    
    return ImpactScore(
        noise=band(300, 700),
        traffic=band(500, 1000),
        dust=ImpactRating.low,
        duration_days=duration_days,
    )
