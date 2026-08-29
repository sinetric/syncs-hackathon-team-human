"""Small, cached forward-geocoder for user-entered Australian addresses.

The public Nominatim endpoint is called only when the user saves a place (never
for autocomplete), cached for a day, identified with a custom User-Agent, and
rate-limited to one request per second as required by its usage policy.
"""

from __future__ import annotations

import threading
import time

import requests

from alerts.cache import cached
from config import GEOCODE_CACHE_TTL_S

_URL = "https://nominatim.openstreetmap.org/search"
_HEADERS = {"User-Agent": "KnowAhead/0.2 (https://github.com/sinetric/syncs-hackathon-team-human)"}
_rate_lock = threading.Lock()
_last_request_at = 0.0


def geocode_address(address: str) -> dict | None:
    query = " ".join(address.split()).strip()
    if not query:
        return None

    def fetch() -> dict | None:
        global _last_request_at
        with _rate_lock:
            wait = 1.0 - (time.monotonic() - _last_request_at)
            if wait > 0:
                time.sleep(wait)
            response = requests.get(
                _URL,
                params={"q": query, "format": "jsonv2", "limit": 1, "countrycodes": "au"},
                headers=_HEADERS,
                timeout=12,
            )
            _last_request_at = time.monotonic()
        response.raise_for_status()
        rows = response.json()
        if not rows:
            return None
        result = rows[0]
        return {
            "address": result["display_name"],
            "lat": float(result["lat"]),
            "lng": float(result["lon"]),
            "source": "OpenStreetMap Nominatim",
        }

    return cached(f"geocode:{query.casefold()}", fetch, ttl_s=GEOCODE_CACHE_TTL_S)
