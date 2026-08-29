"""
Journey preview — legs, fare estimate, trip mode, pre-departure checklist,
and the alerts scoped to that journey.

DEMO_MODE transit journeys come from fixtures/journey_transit.json (a
realistic trackwork itinerary with a rail-replacement bus); live mode uses a
deterministic distance-based estimate, clearly labelled — the real TfNSW trip
planner slots in behind build_preview later without touching the contract.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from config import DEMO_MODE, FIXTURES_DIR
from alerts import gather_events
from alerts.matcher import _near_corridor
from alerts.scorer import actions_for, score
from geo import haversine_m
from models import (
    Alert,
    AlertAffects,
    AlertGeo,
    AlertKind,
    AlertSource,
    ChecklistItem,
    Fare,
    JourneyLeg,
    JourneyPreview,
    LegMode,
    Place,
    Severity,
    TravelMode,
    TripMode,
)
from timeutil import to_syd

import hashlib

# ---------------------------------------------------------------------------
# Fares — static Opal fare-band table (adult, rail) by straight-line distance.
# An estimate by design: basis strings say so and the UI labels it.
# ---------------------------------------------------------------------------

_OPAL_BANDS = [  # (max_km, peak_cents, offpeak_cents)
    (10, 420, 294),
    (20, 521, 364),
    (35, 599, 419),
    (65, 802, 561),
    (float("inf"), 1031, 721),
]


def _is_peak(depart_at: datetime) -> bool:
    if depart_at.weekday() >= 5:
        return False
    minutes = depart_at.hour * 60 + depart_at.minute
    return (6 * 60 + 30) <= minutes < 10 * 60 or 15 * 60 <= minutes < 19 * 60


def estimate_fare(distance_km: float, depart_at: datetime, mode: TravelMode) -> Fare:
    if mode == TravelMode.walk:
        return Fare(estimate_cents=0, basis="free")
    if mode == TravelMode.drive:
        # rough running cost, not a toll calculation
        return Fare(estimate_cents=round(distance_km * 25), basis="fuel_estimate")
    peak = _is_peak(depart_at)
    for max_km, peak_cents, offpeak_cents in _OPAL_BANDS:
        if distance_km <= max_km:
            return Fare(
                estimate_cents=peak_cents if peak else offpeak_cents,
                basis="opal_adult_peak" if peak else "opal_adult_offpeak",
            )
    raise AssertionError("unreachable")


# ---------------------------------------------------------------------------
# Checklist — rules-based, keyed off trip_mode, weather alerts, and leg modes.
# ---------------------------------------------------------------------------


def build_checklist(
    trip_mode: TripMode, legs: list[JourneyLeg], alerts: list[Alert], duration_minutes: int
) -> list[ChecklistItem]:
    items: list[ChecklistItem] = []
    leg_modes = {leg.mode for leg in legs}

    if LegMode.drive in leg_modes:
        items.append(ChecklistItem(id="chk_fuel", label="Fuel or battery",
                                   reason="You're driving — check before you leave"))
    if leg_modes & {LegMode.train, LegMode.bus, LegMode.lightrail, LegMode.ferry}:
        items.append(ChecklistItem(id="chk_ticket", label="Opal card or contactless",
                                   reason="Transit legs on this trip"))
    if any(a.kind == AlertKind.weather for a in alerts):
        items.append(ChecklistItem(id="chk_umbrella", label="Umbrella",
                                   reason="Rain is likely along the way"))
    if trip_mode == TripMode.long:
        items.append(ChecklistItem(id="chk_water", label="Water bottle",
                                   reason=f"{duration_minutes} min trip"))
        items.append(ChecklistItem(id="chk_toilet", label="Bathroom before you go",
                                   reason="Long trip — interchange stops have toilets"))
        items.append(ChecklistItem(id="chk_charge", label="Phone charged",
                                   reason="You'll want live updates en route"))
    return items


# ---------------------------------------------------------------------------
# Leg builders
# ---------------------------------------------------------------------------


def _legs_from_fixture(origin: Place, dest: Place, depart_at: datetime) -> list[JourneyLeg] | None:
    path = FIXTURES_DIR / "journey_transit.json"
    if not path.exists():
        return None
    template = json.loads(path.read_text(encoding="utf-8"))
    legs: list[JourneyLeg] = []
    cursor = depart_at
    for i, item in enumerate(template):
        duration = int(item["duration_minutes"])
        arrive = cursor + timedelta(minutes=duration)
        legs.append(
            JourneyLeg(
                index=i,
                mode=LegMode(item["mode"]),
                **{"from": item["from"].replace("{origin}", origin.label)},
                to=item["to"].replace("{dest}", dest.label),
                depart_at=cursor,
                arrive_at=arrive,
                line=item.get("line"),
                duration_minutes=duration,
            )
        )
        cursor = arrive
    return legs


def _legs_estimated(
    origin: Place, dest: Place, depart_at: datetime, mode: TravelMode, distance_km: float
) -> list[JourneyLeg]:
    def leg(i: int, leg_mode: LegMode, frm: str, to: str, start: datetime,
            mins: int, line: str | None = None) -> JourneyLeg:
        return JourneyLeg(
            index=i, mode=leg_mode, **{"from": frm}, to=to, depart_at=start,
            arrive_at=start + timedelta(minutes=mins), line=line, duration_minutes=mins,
        )

    if mode == TravelMode.walk:
        mins = max(5, round(distance_km * 1000 / 80))
        return [leg(0, LegMode.walk, origin.label, dest.label, depart_at, mins)]
    if mode == TravelMode.drive:
        mins = max(8, round(distance_km * 2) + 5)
        return [leg(0, LegMode.drive, origin.label, dest.label, depart_at, mins)]

    walk1 = 8
    ride = max(10, round(distance_km * 1.7) + 6)
    walk2 = 10
    t1 = depart_at + timedelta(minutes=walk1)
    t2 = t1 + timedelta(minutes=ride)
    return [
        leg(0, LegMode.walk, origin.label, "Nearest station", depart_at, walk1),
        leg(1, LegMode.train, "Nearest station", "Interchange", t1, ride, line="rail"),
        leg(2, LegMode.walk, "Interchange", dest.label, t2, walk2),
    ]


# ---------------------------------------------------------------------------
# Journey-scoped alerts
# ---------------------------------------------------------------------------


def _journey_alerts(
    origin: Place, dest: Place, depart_at: datetime, legs: list[JourneyLeg], mode: TravelMode
) -> list[Alert]:
    window_start = depart_at - timedelta(minutes=30)
    window_end = legs[-1].arrive_at + timedelta(minutes=30)
    first_ride_index = next(
        (leg.index for leg in legs if leg.mode not in (LegMode.walk, LegMode.drive)), None
    )

    alerts: list[Alert] = []
    for event in gather_events():
        if event.valid_to < window_start or event.valid_from > window_end:
            continue
        if event.kind == AlertKind.transport_disruption and mode != TravelMode.transit:
            continue
        if event.lat is None or event.lng is None:
            if not (event.lines and mode == TravelMode.transit):
                continue
        elif not _near_corridor(event, origin, dest):
            continue

        severity, impact = score(event, affects_routine=True)
        alerts.append(
            Alert(
                id="alt_" + hashlib.sha1(event.uid.encode()).hexdigest()[:12],
                kind=event.kind,
                severity=severity,
                title=event.title,
                body=event.body,
                impact=impact,
                affects=AlertAffects(
                    leg_index=first_ride_index
                    if event.kind == AlertKind.transport_disruption else None,
                ),
                valid_from=event.valid_from,
                valid_to=event.valid_to,
                geo=(
                    AlertGeo(lat=event.lat, lng=event.lng, radius_m=event.radius_m)
                    if event.lat is not None and event.lng is not None else None
                ),
                actions=actions_for(event, severity, impact),
                source=AlertSource(
                    name=event.source_name, url=event.source_url, fetched_at=event.fetched_at
                ),
            )
        )
    return alerts


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def build_preview(
    origin: Place, dest: Place, depart_at: datetime, mode: TravelMode
) -> JourneyPreview:
    depart_at = to_syd(depart_at)
    distance_km = haversine_m(origin.lat, origin.lng, dest.lat, dest.lng) / 1000

    legs: list[JourneyLeg] | None = None
    if DEMO_MODE and mode == TravelMode.transit:
        legs = _legs_from_fixture(origin, dest, depart_at)
    if legs is None:
        legs = _legs_estimated(origin, dest, depart_at, mode, distance_km)

    alerts = _journey_alerts(origin, dest, depart_at, legs, mode)

    # live delays push the affected leg (and the total) out — the preview
    # reflects the network as it is now, not the printed timetable
    worst_delay = max(
        (a.impact.delay_minutes or 0 for a in alerts if a.severity != Severity.info),
        default=0,
    )
    duration = sum(leg.duration_minutes for leg in legs) + worst_delay
    trip_mode = TripMode.long if duration > 60 else TripMode.short

    checklist = build_checklist(trip_mode, legs, alerts, duration)
    fare = estimate_fare(distance_km, depart_at, mode)

    return JourneyPreview(
        duration_minutes=duration,
        trip_mode=trip_mode,
        legs=legs,
        fare=fare,
        checklist=checklist,
        alerts=alerts,
    )
