"""
Matcher — decides whether a source event intersects a routine or place.

A routine matches when BOTH hold:
  * geo: the event sits within CORRIDOR_RADIUS_M of the route corridor
    (v1: points sampled along the straight line origin -> destination —
    a knowingly coarse corridor; swap in trip-planner leg coordinates later),
    or the event has no coordinates but names a transit line (system-wide
    disruptions match transit routines).
  * time: the event's validity overlaps the routine's departure window
    (depart - DEPART_WINDOW_BEFORE_MIN, depart + DEPART_WINDOW_AFTER_MIN)
    for the routine's next scheduled departure.

A place matches on geo alone (radius against the saved point).
"""

from __future__ import annotations

from datetime import timedelta

from config import CORRIDOR_RADIUS_M, DEPART_WINDOW_AFTER_MIN, DEPART_WINDOW_BEFORE_MIN
from alerts.events import SourceEvent
from geo import haversine_m
from models import AlertKind, Place, Routine, TravelMode
from timeutil import next_departure

_CORRIDOR_SAMPLES = 12


def _corridor_points(origin: Place, dest: Place) -> list[tuple[float, float]]:
    return [
        (
            origin.lat + (dest.lat - origin.lat) * i / _CORRIDOR_SAMPLES,
            origin.lng + (dest.lng - origin.lng) * i / _CORRIDOR_SAMPLES,
        )
        for i in range(_CORRIDOR_SAMPLES + 1)
    ]


def _near_corridor(event: SourceEvent, origin: Place, dest: Place) -> bool:
    if event.lat is None or event.lng is None:
        return False
    reach = max(CORRIDOR_RADIUS_M, event.radius_m)
    return any(
        haversine_m(lat, lng, event.lat, event.lng) <= reach
        for lat, lng in _corridor_points(origin, dest)
    )


def matches_routine(event: SourceEvent, routine: Routine, origin: Place, dest: Place) -> bool:
    depart = next_departure([d.value for d in routine.days], routine.depart_local_time)
    if depart is None:
        return False
    window_start = depart - timedelta(minutes=DEPART_WINDOW_BEFORE_MIN)
    window_end = depart + timedelta(minutes=DEPART_WINDOW_AFTER_MIN)
    if event.valid_to < window_start or event.valid_from > window_end:
        return False

    if event.kind == AlertKind.transport_disruption and routine.mode != TravelMode.transit:
        return False
    if event.kind in (AlertKind.roadwork, AlertKind.incident) and routine.mode == TravelMode.transit:
        # a road closure can still hit the walk/bus legs, so keep geo matching
        pass

    if event.lat is None or event.lng is None:
        # no coordinates: only line-tagged transit disruptions can match
        return bool(event.lines) and routine.mode == TravelMode.transit
    return _near_corridor(event, origin, dest)


def matches_place(event: SourceEvent, place: Place) -> bool:
    if event.lat is None or event.lng is None:
        return False
    reach = max(1000, event.radius_m)
    return haversine_m(place.lat, place.lng, event.lat, event.lng) <= reach
