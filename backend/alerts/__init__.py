"""
Alert engine — the actual product.

    adapters (normalised SourceEvents, fixtures in DEMO_MODE)
        -> dedupe (same source + same underlying event id emits once)
        -> matcher (geo corridor/place intersection AND time overlap)
        -> scorer (severity + impact.delay_minutes)
        -> Alert objects per docs/api-contract.md
    plus computed leave-now reminders per routine.
"""

from __future__ import annotations

import hashlib
from datetime import timedelta

from alerts.adapters import ADAPTERS
from alerts.events import SourceEvent
from alerts.matcher import matches_place, matches_routine
from alerts.scorer import actions_for, score
from models import (
    Alert,
    AlertAction,
    AlertAffects,
    AlertGeo,
    AlertImpact,
    AlertKind,
    AlertSource,
    Place,
    Routine,
    Severity,
)
from store import load_places, load_routines
from timeutil import next_departure, now_syd

_SEVERITY_ORDER = {Severity.act: 0, Severity.watch: 1, Severity.info: 2}


def _alert_id(uid: str) -> str:
    return "alt_" + hashlib.sha1(uid.encode()).hexdigest()[:12]


def gather_events() -> list[SourceEvent]:
    """All adapter events, deduped on uid (first adapter wins)."""
    seen: set[str] = set()
    events: list[SourceEvent] = []
    for adapter in ADAPTERS:
        for event in adapter.events():
            if event.uid in seen:
                continue
            seen.add(event.uid)
            events.append(event)
    return events


def build_alerts(
    routine_id: str | None = None,
    place_id: str | None = None,
    window_mins: int = 180,
) -> list[Alert]:
    now = now_syd()
    horizon = now + timedelta(minutes=window_mins)

    places = {p.id: p for p in load_places()}
    routines = [r for r in load_routines() if r.origin_id in places and r.dest_id in places]
    if routine_id:
        routines = [r for r in routines if r.id == routine_id]
    watch_places = list(places.values())
    if place_id:
        watch_places = [p for p in watch_places if p.id == place_id]

    alerts: list[Alert] = []
    for event in gather_events():
        if event.valid_to < now or event.valid_from > horizon:
            continue

        matched_routines = [
            r for r in routines
            if matches_routine(event, r, places[r.origin_id], places[r.dest_id])
        ]
        matched_places = [p for p in watch_places if matches_place(event, p)]
        if routine_id and not matched_routines:
            continue
        if place_id and not matched_places:
            continue
        if not matched_routines and not matched_places:
            continue

        severity, impact = score(event, affects_routine=bool(matched_routines))
        body = event.body
        if matched_routines and event.kind != AlertKind.construction:
            names = ", ".join(f"your {r.name.lower()}" for r in matched_routines[:2])
            body = f"{body} Affects {names}." if body else f"Affects {names}."
        alerts.append(
            Alert(
                id=_alert_id(event.uid),
                kind=event.kind,
                severity=severity,
                title=event.title,
                body=body,
                impact=impact,
                affects=AlertAffects(
                    routine_ids=[r.id for r in matched_routines],
                    place_ids=[p.id for p in matched_places],
                    leg_index=None,
                ),
                valid_from=event.valid_from,
                valid_to=event.valid_to,
                geo=(
                    AlertGeo(lat=event.lat, lng=event.lng, radius_m=event.radius_m)
                    if event.lat is not None and event.lng is not None
                    else None
                ),
                actions=actions_for(event, severity, impact),
                source=AlertSource(
                    name=event.source_name, url=event.source_url, fetched_at=event.fetched_at
                ),
            )
        )

    if not place_id:
        alerts.extend(_leave_now_reminders(routines, alerts, window_mins))

    alerts.sort(key=lambda a: (_SEVERITY_ORDER[a.severity], a.valid_from))
    return alerts


def _leave_now_reminders(
    routines: list[Routine], alerts: list[Alert], window_mins: int
) -> list[Alert]:
    """Computed from the routine + live delay, not a dumb alarm: the leave time
    is the routine's departure pulled forward by the worst matched delay."""
    now = now_syd()
    reminders: list[Alert] = []
    for routine in routines:
        depart = next_departure([d.value for d in routine.days], routine.depart_local_time)
        if depart is None or depart > now + timedelta(minutes=window_mins):
            continue
        delay = max(
            (
                a.impact.delay_minutes or 0
                for a in alerts
                if routine.id in a.affects.routine_ids and a.severity != Severity.info
            ),
            default=0,
        )
        leave_at = depart - timedelta(minutes=delay)
        mins_left = int((leave_at - now).total_seconds() // 60)
        if mins_left < 0:
            continue
        if delay:
            body = (
                f"Delays add {delay} min to your {routine.name.lower()}. "
                f"Leave by {leave_at.strftime('%H:%M')} instead of {depart.strftime('%H:%M')}."
            )
        else:
            body = f"Your {routine.name.lower()} departs {depart.strftime('%H:%M')}. No delays so far."
        reminders.append(
            Alert(
                id=_alert_id(f"reminder:{routine.id}:{depart.isoformat()}"),
                kind=AlertKind.reminder,
                severity=Severity.act if mins_left <= 45 else Severity.watch,
                title=f"Leave by {leave_at.strftime('%H:%M')} for your {routine.name.lower()}",
                body=body,
                impact=AlertImpact(delay_minutes=delay or None, confidence=0.8),
                affects=AlertAffects(routine_ids=[routine.id]),
                valid_from=now,
                valid_to=depart,
                geo=None,
                actions=[
                    AlertAction(
                        type="leave_earlier",
                        label="Remind me 10 min before",
                        payload={"minutes": 10, "leave_at": leave_at.isoformat()},
                    )
                ],
                source=AlertSource(name="Know Ahead", url=None, fetched_at=now),
            )
        )
    return reminders
