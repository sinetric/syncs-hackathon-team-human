"""
Live Traffic NSW — open incident + roadwork hazard feeds (no key needed).

https://www.livetraffic.com — data.livetraffic.com publishes GeoJSON-ish
hazard files refreshed every minute.
"""

from __future__ import annotations

import requests

from alerts.adapters.base import SourceAdapter
from alerts.events import SourceEvent
from models import AlertKind
from timeutil import now_syd, to_syd

from datetime import datetime, timedelta

_FEEDS = {
    "incident": "https://data.livetraffic.com/traffic/hazards/incident-open.json",
    "roadwork": "https://data.livetraffic.com/traffic/hazards/roadwork.json",
}


class LiveTrafficAdapter(SourceAdapter):
    name = "livetraffic"
    display_name = "Live Traffic NSW"
    url = "https://www.livetraffic.com"

    def fetch_live(self) -> list[SourceEvent]:
        now = now_syd()
        events: list[SourceEvent] = []
        for feed_kind, feed_url in _FEEDS.items():
            resp = requests.get(feed_url, timeout=10)
            resp.raise_for_status()
            for feature in resp.json().get("features", []):
                props = feature.get("properties", {})
                coords = (feature.get("geometry") or {}).get("coordinates") or [None, None]
                created_ms = props.get("created")
                valid_from = (
                    to_syd(datetime.fromtimestamp(created_ms / 1000)) if created_ms else now
                )
                events.append(
                    SourceEvent(
                        uid=f"livetraffic:{feature.get('id')}",
                        kind=AlertKind.roadwork if feed_kind == "roadwork" else AlertKind.incident,
                        title=props.get("displayName") or props.get("headline", "Road hazard"),
                        body=(props.get("otherAdvice") or props.get("adviceA") or "")[:400],
                        lat=coords[1],
                        lng=coords[0],
                        radius_m=500,
                        valid_from=valid_from,
                        valid_to=now + timedelta(hours=6),
                        source_name=self.display_name,
                        source_url=self.url,
                        fetched_at=now,
                    )
                )
        return events
