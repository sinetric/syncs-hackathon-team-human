"""
Scorer — sets severity and impact from matcher output. The backend owns
severity (contract rule); the frontend never recomputes it.

  act   — user must change behaviour now (leave earlier, reroute)
  watch — will matter within the window but no action yet
  info  — context only (construction near home, rain later)
"""

from __future__ import annotations

from alerts.events import SourceEvent
from models import (
    AlertAction,
    AlertImpact,
    AlertKind,
    Severity,
)


def score(event: SourceEvent, affects_routine: bool) -> tuple[Severity, AlertImpact]:
    delay = event.delay_minutes

    if event.kind == AlertKind.transport_disruption:
        if affects_routine and delay is not None and delay >= 10:
            return Severity.act, AlertImpact(delay_minutes=delay, confidence=0.72)
        if affects_routine and delay is not None:
            return Severity.watch, AlertImpact(delay_minutes=delay, confidence=0.65)
        return (
            Severity.watch if affects_routine else Severity.info,
            AlertImpact(delay_minutes=delay, confidence=0.5),
        )

    if event.kind == AlertKind.incident:
        estimated = delay if delay is not None else 8
        if affects_routine:
            return Severity.act if estimated >= 10 else Severity.watch, AlertImpact(
                delay_minutes=estimated, confidence=0.55
            )
        return Severity.info, AlertImpact(delay_minutes=None, confidence=0.5)

    if event.kind == AlertKind.roadwork:
        return (
            Severity.watch if affects_routine else Severity.info,
            AlertImpact(delay_minutes=delay if delay is not None else 5, confidence=0.6),
        )

    if event.kind == AlertKind.weather:
        return (
            Severity.watch if affects_routine else Severity.info,
            AlertImpact(delay_minutes=None, confidence=0.7),
        )

    # construction / advice / anything new: context only
    return Severity.info, AlertImpact(delay_minutes=None, confidence=0.6)


def actions_for(event: SourceEvent, severity: Severity, impact: AlertImpact) -> list[AlertAction]:
    actions: list[AlertAction] = []
    if severity == Severity.act and impact.delay_minutes:
        actions.append(
            AlertAction(
                type="leave_earlier",
                label=f"Leave {impact.delay_minutes} min earlier",
                payload={"minutes": impact.delay_minutes},
            )
        )
    if event.kind in (AlertKind.transport_disruption, AlertKind.incident, AlertKind.roadwork):
        actions.append(AlertAction(type="reroute", label="Show alternative"))
    return actions
