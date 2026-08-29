"""
Parking service: real parking locations from OSM plus an estimated
probability of finding a spot.

There is no live occupancy source wired in, so the probability is an
explicitly-labelled heuristic estimate built only from signals we actually
have: OSM attributes (type, access, fee, capacity), time of day and weekday,
active nearby event/disruption alerts, and current rain. Every estimate
carries the reasons that produced it.
"""

from __future__ import annotations

from datetime import datetime

from geo import haversine_m
from services.overpass import fetch_features


def find_parking(
    lat: float,
    lng: float,
    radius_m: int = 1200,
    now: datetime | None = None,
    nearby_event_count: int = 0,
    raining: bool = False,
    timeout_s: int = 15,
    max_mirrors: int | None = None,
) -> tuple[list[dict], bool]:
    """Return (parking spots sorted nearest-first, overpass_available)."""
    features, available = fetch_features(
        lat,
        lng,
        radius_m,
        kinds=["parking"],
        timeout_s=timeout_s,
        max_mirrors=max_mirrors,
    )
    spots = []
    for f in features:
        distance = round(haversine_m(lat, lng, f["lat"], f["lng"]))
        probability, reasons = _estimate_probability(
            f["tags"], distance, now, nearby_event_count, raining
        )
        spots.append(
            {
                **f,
                "distance_m": distance,
                "probability": {
                    "value_pct": probability,
                    "label": "Estimated parking probability",
                    "basis": "heuristic estimate — no live occupancy source",
                    "reasons": reasons,
                },
            }
        )
    spots.sort(key=lambda s: s["distance_m"])
    return spots[:25], available


def _estimate_probability(
    tags: dict,
    distance_m: int,
    now: datetime | None,
    nearby_event_count: int,
    raining: bool,
) -> tuple[int, list[str]]:
    score = 60.0
    reasons: list[str] = []

    access = tags.get("access", "")
    if access in ("private", "no"):
        score -= 45
        reasons.append("Marked private on OSM — likely not open to the public")
    elif access == "customers":
        score -= 15
        reasons.append("Customers-only access")
    elif access in ("yes", "public", "permissive", ""):
        reasons.append("Publicly accessible" if access else "Access not tagged — assumed public")

    variant = tags.get("parking", "")
    if variant in ("multi-storey", "underground"):
        score += 15
        reasons.append(f"{variant.replace('-', ' ').title()} — larger turnover than street parking")
    elif variant == "surface":
        score += 5
        reasons.append("Surface car park")
    elif variant in ("street_side", "lane"):
        score -= 10
        reasons.append("Street parking — fills fast")

    if tags.get("fee") == "yes":
        score += 8
        reasons.append("Paid parking — usually higher availability")
    capacity = tags.get("capacity")
    if capacity and str(capacity).isdigit():
        cap = int(capacity)
        if cap >= 100:
            score += 10
            reasons.append(f"Large capacity (~{cap} spaces)")
        elif cap < 20:
            score -= 8
            reasons.append(f"Small capacity (~{cap} spaces)")

    if now is not None:
        weekday = now.weekday() < 5
        if weekday and 8 <= now.hour < 18:
            score -= 15
            reasons.append("Weekday business hours — demand is high")
        elif now.hour >= 22 or now.hour < 6:
            score += 15
            reasons.append("Late night — demand is low")
        elif not weekday and 10 <= now.hour < 16:
            score -= 8
            reasons.append("Weekend daytime demand")

    if nearby_event_count:
        score -= min(25, 10 * nearby_event_count)
        reasons.append(
            f"{nearby_event_count} active event/disruption alert(s) nearby increase demand"
        )
    if raining:
        score -= 7
        reasons.append("Rain pushes more people into cars")

    if distance_m > 600:
        score += 8
        reasons.append("Further from the destination — less contested")

    return max(3, min(97, round(score))), reasons
