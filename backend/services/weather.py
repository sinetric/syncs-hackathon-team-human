"""
Live weather service (Open-Meteo, no key needed).

Always live — even in DEMO_MODE — because it's keyless and the requirement is
that weather genuinely influences decisions. If the network is down it
returns available=False and the callers (journey impact, AI, UI) say
"weather unavailable" instead of inventing conditions.

The response separates *observed* fields (straight from the API) from
*derived* signals (our interpretation, labelled as such).
"""

from __future__ import annotations

import logging

import requests

from alerts.cache import cached
from timeutil import now_syd

log = logging.getLogger("knowahead.weather")

_URL = "https://api.open-meteo.com/v1/forecast"
_TIMEOUT_S = 8
_CACHE_TTL_S = 300

# WMO weather interpretation codes -> label
_WMO = {
    0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime fog", 51: "Light drizzle", 53: "Drizzle",
    55: "Heavy drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
    66: "Freezing rain", 67: "Heavy freezing rain", 71: "Light snow",
    73: "Snow", 75: "Heavy snow", 80: "Rain showers", 81: "Heavy showers",
    82: "Violent showers", 95: "Thunderstorm", 96: "Thunderstorm with hail",
    99: "Severe thunderstorm",
}


def get_weather(lat: float, lng: float) -> tuple[dict | None, bool]:
    """Return (weather, available)."""
    key = f"weather:{round(lat, 3)}:{round(lng, 3)}"
    try:
        return cached(key, lambda: _fetch(lat, lng), ttl_s=_CACHE_TTL_S), True
    except Exception:
        log.exception("open-meteo unavailable")
        return None, False


def _fetch(lat: float, lng: float) -> dict:
    resp = requests.get(
        _URL,
        params={
            "latitude": lat,
            "longitude": lng,
            "current": "temperature_2m,precipitation,rain,weather_code,wind_speed_10m,wind_gusts_10m",
            "hourly": "precipitation_probability,precipitation,wind_gusts_10m",
            "timezone": "Australia/Sydney",
            "forecast_days": 1,
        },
        timeout=_TIMEOUT_S,
    )
    resp.raise_for_status()
    data = resp.json()
    current = data.get("current", {})
    hourly = data.get("hourly", {})

    now = now_syd()
    hour_index = now.hour
    probs = (hourly.get("precipitation_probability") or [])[hour_index : hour_index + 12]
    gusts = (hourly.get("wind_gusts_10m") or [])[hour_index : hour_index + 12]
    max_rain_prob = max((p for p in probs if p is not None), default=None)
    max_gust = max((g for g in gusts if g is not None), default=None)

    code = current.get("weather_code")
    observed = {
        "temperature_c": current.get("temperature_2m"),
        "precipitation_mm": current.get("precipitation"),
        "rain_mm": current.get("rain"),
        "wind_speed_kmh": current.get("wind_speed_10m"),
        "wind_gusts_kmh": current.get("wind_gusts_10m"),
        "weather_code": code,
        "conditions": _WMO.get(code, "Unknown"),
    }

    # our interpretation of the observed numbers — labelled derived, not fact
    signals: list[str] = []
    raining_now = (current.get("rain") or 0) > 0.2 or (code or 0) in (61, 63, 65, 80, 81, 82, 95, 96, 99)
    if raining_now:
        signals.append("Rain is falling now — wet roads and slower traffic are likely.")
    if max_rain_prob is not None and max_rain_prob >= 60 and not raining_now:
        signals.append(f"Rain is likely later ({max_rain_prob}% within 12 h).")
    if (code or 0) in (65, 82, 95, 96, 99):
        signals.append("Heavy rain or storms — localised flooding is possible in low-lying areas.")
    if max_gust is not None and max_gust >= 60:
        signals.append(f"Strong wind gusts expected (up to {round(max_gust)} km/h).")

    return {
        "observed": observed,
        "derived": {
            "raining_now": raining_now,
            "max_rain_probability_12h_pct": max_rain_prob,
            "max_wind_gust_12h_kmh": max_gust,
            "signals": signals,
            "basis": "derived from Open-Meteo observations — an interpretation, not a warning product",
        },
        "source": {
            "name": "Open-Meteo",
            "url": "https://open-meteo.com",
            "fetched_at": now.isoformat(),
        },
    }
