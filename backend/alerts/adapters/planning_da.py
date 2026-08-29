"""
NSW Planning Portal — development applications near saved places.

The live "Online DA Data API" needs a subscription key requested by email
(not obtainable same-day), so both modes currently read the repo's seed file
via the existing sources/planning.py adapter. Swap fetch_live's body for a
real request once a key is issued — nothing downstream changes.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta

from alerts.adapters.base import SourceAdapter
from alerts.events import SourceEvent
from models import AlertKind
from sources.planning import fetch_planning_events
from timeutil import SYDNEY, now_syd


class PlanningAdapter(SourceAdapter):
    name = "planning"
    display_name = "NSW Planning Portal"
    url = "https://www.planningportal.nsw.gov.au"

    def fetch_live(self) -> list[SourceEvent]:
        now = now_syd()
        events: list[SourceEvent] = []
        for ev in fetch_planning_events():
            valid_from = (
                datetime.combine(ev.start_date, time.min, tzinfo=SYDNEY)
                if ev.start_date else now
            )
            valid_to = (
                datetime.combine(ev.end_date, time.max, tzinfo=SYDNEY)
                if ev.end_date else now + timedelta(days=365)
            )
            events.append(
                SourceEvent(
                    uid=f"planning:{ev.id}",
                    kind=AlertKind.construction,
                    title=ev.title,
                    body=ev.description[:400],
                    lat=ev.latitude,
                    lng=ev.longitude,
                    radius_m=400,
                    valid_from=valid_from,
                    valid_to=valid_to,
                    source_name=self.display_name,
                    source_url=self.url,
                    fetched_at=now,
                )
            )
        return events
