"""
Transport for NSW Open Data — service alerts.

Live path uses the Trip Planner "add_info" endpoint (JSON service alerts),
which covers the same disruption feed as GTFS-Realtime without a protobuf
dependency. Requires TFNSW_API_KEY (free account at
https://opendata.transport.nsw.gov.au — approval can take a while, hence
DEMO_MODE fixtures).
"""

from __future__ import annotations

import re

import requests

from config import TFNSW_API_KEY
from alerts.adapters.base import SourceAdapter
from alerts.events import SourceEvent
from models import AlertKind
from timeutil import now_syd, parse_iso_syd

_ADD_INFO_URL = "https://api.transport.nsw.gov.au/v1/tp/add_info"

_DELAY_RE = re.compile(r"(?:delay(?:s|ed)?[^0-9]{0,20})(\d{1,3})\s*min", re.IGNORECASE)


class TfnswAdapter(SourceAdapter):
    name = "tfnsw"
    display_name = "Transport for NSW"
    url = "https://transportnsw.info/alerts"

    def fetch_live(self) -> list[SourceEvent]:
        resp = requests.get(
            _ADD_INFO_URL,
            params={"outputFormat": "rapidJSON", "filterPublicationStatus": "current"},
            headers={"Authorization": f"apikey {TFNSW_API_KEY}"},
            timeout=10,
        )
        resp.raise_for_status()
        now = now_syd()
        events: list[SourceEvent] = []
        for info in resp.json().get("infos", {}).get("current", []):
            timestamps = info.get("timestamps", {})
            validity = (timestamps.get("validity") or [{}])[0]
            title = info.get("subtitle") or info.get("urlText") or "Service alert"
            body = re.sub(r"<[^>]+>", " ", info.get("content", "")).strip()
            match = _DELAY_RE.search(f"{title} {body}")
            lines = [
                a.get("number") or a.get("name", "")
                for a in info.get("affected", {}).get("lines", [])
            ]
            events.append(
                SourceEvent(
                    uid=f"tfnsw:{info.get('id')}",
                    kind=AlertKind.transport_disruption,
                    title=title,
                    body=body[:400],
                    delay_minutes=int(match.group(1)) if match else None,
                    lines=[ln for ln in lines if ln],
                    valid_from=parse_iso_syd(validity["from"]) if validity.get("from") else now,
                    valid_to=parse_iso_syd(validity["to"]) if validity.get("to") else now,
                    source_name=self.display_name,
                    source_url=info.get("url") or self.url,
                    fetched_at=now,
                )
            )
        return events
