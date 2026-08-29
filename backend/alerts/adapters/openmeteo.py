"""
Open-Meteo — hourly precipitation probability per saved place. No API key.

Emits one weather event per place whose next 12 hours include an hour with
>= 60% precipitation probability. The event is pinned to the place's
coordinates so the matcher treats it like any other geo event.
"""

from __future__ import annotations

from datetime import timedelta

import requests

from alerts.adapters.base import SourceAdapter
from alerts.events import SourceEvent
from models import AlertKind
from store import load_places
from timeutil import now_syd, parse_iso_syd

_URL = "https://api.open-meteo.com/v1/forecast"
_RAIN_THRESHOLD_PCT = 60


class OpenMeteoAdapter(SourceAdapter):
    name = "openmeteo"
    display_name = "Open-Meteo"
    url = "https://open-meteo.com"

    def fetch_live(self) -> list[SourceEvent]:
        now = now_syd()
        events: list[SourceEvent] = []
        for place in load_places():
            resp = requests.get(
                _URL,
                params={
                    "latitude": place.lat,
                    "longitude": place.lng,
                    "hourly": "precipitation_probability",
                    "timezone": "Australia/Sydney",
                    "forecast_days": 1,
                },
                timeout=10,
            )
            resp.raise_for_status()
            hourly = resp.json().get("hourly", {})
            times = hourly.get("time", [])
            probs = hourly.get("precipitation_probability", [])
            for iso, prob in zip(times, probs):
                if prob is None or prob < _RAIN_THRESHOLD_PCT:
                    continue
                hour = parse_iso_syd(iso)
                if not (now <= hour <= now + timedelta(hours=12)):
                    continue
                events.append(
                    SourceEvent(
                        uid=f"openmeteo:{place.id}:{iso}",
                        kind=AlertKind.weather,
                        title=f"Rain likely near {place.label} ({prob}%)",
                        body=f"{prob}% chance of rain around {hour.strftime('%I%p').lstrip('0').lower()} near {place.label}.",
                        lat=place.lat,
                        lng=place.lng,
                        radius_m=3000,
                        valid_from=hour - timedelta(hours=1),
                        valid_to=hour + timedelta(hours=1),
                        source_name=self.display_name,
                        source_url=self.url,
                        fetched_at=now,
                    )
                )
                break  # one rain event per place is enough signal
        return events
