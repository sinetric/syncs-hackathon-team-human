"""
Data-source registry.

Add a source module here and it flows through the whole pipeline
(change detection -> geo filter -> impact scoring) unchanged.
"""

from __future__ import annotations

from models import UrbanEvent
from sources.planning import fetch_planning_events


def fetch_all_events() -> list[UrbanEvent]:
    events: list[UrbanEvent] = []
    events += fetch_planning_events()
    # events += fetch_roadwork_events()   # TODO: TfNSW Live Traffic hazards API
    # events += fetch_weather_events()    # TODO: Bureau of Meteorology
    return events
