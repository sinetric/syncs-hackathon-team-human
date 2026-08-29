"""
Overpass / OpenStreetMap service.

Queries the public Overpass API for real mapped infrastructure around a
point: parking, construction sites, roadworks, and event-capable venues
(theatres, arts centres, stadiums, event venues, stages).

OSM is a map database, not a live event feed — these are *mapped* objects.
Anything time-dependent (delays, live occupancy) is explicitly NOT claimed
here; the impact/AI layers combine these features with the alert engine and
weather to estimate consequences, always labelled as estimates.
"""

from __future__ import annotations

import logging

import requests

from alerts.cache import cached
from timeutil import now_syd

log = logging.getLogger("knowahead.overpass")

# main instance plus a mirror — the first one that answers wins
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
_TIMEOUT_S = 15
_CACHE_TTL_S = 300  # OSM objects change slowly; be a polite Overpass citizen

# kind -> overpass selectors (applied to node/way/relation with `around:`)
_KIND_SELECTORS: dict[str, list[str]] = {
    "parking": ['["amenity"="parking"]'],
    "construction": ['["landuse"="construction"]', '["building"="construction"]'],
    "roadwork": ['["highway"="construction"]', '["construction"]["highway"]'],
    "venue": [
        '["amenity"="theatre"]',
        '["amenity"="arts_centre"]',
        '["amenity"="events_venue"]',
        '["amenity"="nightclub"]',
        '["leisure"="stadium"]',
        '["leisure"="stage"]',
    ],
}

ALL_KINDS = list(_KIND_SELECTORS)


def _build_query(lat: float, lng: float, radius_m: int, kinds: list[str]) -> str:
    clauses = []
    for kind in kinds:
        for selector in _KIND_SELECTORS.get(kind, []):
            around = f"(around:{radius_m},{lat:.5f},{lng:.5f})"
            clauses.append(f"node{selector}{around};")
            clauses.append(f"way{selector}{around};")
    body = "\n  ".join(clauses)
    return f"[out:json][timeout:{_TIMEOUT_S - 2}];\n(\n  {body}\n);\nout center tags;"


def _kind_of(tags: dict) -> str | None:
    if tags.get("amenity") == "parking":
        return "parking"
    if tags.get("highway") == "construction" or ("construction" in tags and "highway" in tags):
        return "roadwork"
    if tags.get("landuse") == "construction" or tags.get("building") == "construction":
        return "construction"
    if tags.get("amenity") in ("theatre", "arts_centre", "events_venue", "nightclub"):
        return "venue"
    if tags.get("leisure") in ("stadium", "stage"):
        return "venue"
    return None


def fetch_features(
    lat: float,
    lng: float,
    radius_m: int = 1500,
    kinds: list[str] | None = None,
    timeout_s: int = _TIMEOUT_S,
    max_mirrors: int | None = None,
) -> tuple[list[dict], bool]:
    """Return (features, available). `available=False` means Overpass could
    not be reached and the caller should say so rather than show nothing
    silently. Features:
        { id, kind, name, lat, lng, tags, source }
    """
    kinds = [k for k in (kinds or ALL_KINDS) if k in _KIND_SELECTORS]
    if not kinds:
        return [], True
    # round the cache key so tiny map pans reuse the same upstream response
    key = f"overpass:{round(lat, 3)}:{round(lng, 3)}:{radius_m}:{','.join(sorted(kinds))}"
    try:
        return cached(
            key,
            lambda: _fetch(lat, lng, radius_m, kinds, timeout_s, max_mirrors),
            ttl_s=_CACHE_TTL_S,
        ), True
    except Exception as exc:
        # Availability is already returned to callers; avoid printing a full
        # requests traceback for a normal third-party timeout.
        log.warning("overpass unavailable: %s", exc)
        return [], False


def _fetch(
    lat: float,
    lng: float,
    radius_m: int,
    kinds: list[str],
    timeout_s: int = _TIMEOUT_S,
    max_mirrors: int | None = None,
) -> list[dict]:
    resp = None
    last_error: Exception | None = None
    urls = OVERPASS_URLS[:max_mirrors] if max_mirrors else OVERPASS_URLS
    for url in urls:
        try:
            resp = requests.post(
                url,
                data={"data": _build_query(lat, lng, radius_m, kinds)},
                timeout=timeout_s,
                headers={"User-Agent": "KnowAhead-hackathon/0.3 (contact: repo issues)"},
            )
            resp.raise_for_status()
            break
        except Exception as exc:  # noqa: BLE001 — try the next mirror
            last_error = exc
            resp = None
    if resp is None:
        raise last_error if last_error else RuntimeError("no overpass instance answered")
    fetched_at = now_syd().isoformat()
    features: list[dict] = []
    for el in resp.json().get("elements", []):
        tags = el.get("tags", {})
        kind = _kind_of(tags)
        if kind is None:
            continue
        center = el.get("center") or el  # ways carry a computed center
        el_lat, el_lng = center.get("lat"), center.get("lon")
        if el_lat is None or el_lng is None:
            continue
        features.append(
            {
                "id": f"osm:{el.get('type')}:{el.get('id')}",
                "kind": kind,
                "name": tags.get("name")
                or tags.get("operator")
                or _fallback_name(kind, tags),
                "lat": el_lat,
                "lng": el_lng,
                "tags": {
                    k: v for k, v in tags.items()
                    if k in (
                        "name", "operator", "access", "fee", "capacity", "parking",
                        "opening_hours", "surface", "construction", "amenity",
                        "leisure", "landuse", "building", "maxstay", "website",
                    )
                },
                "source": {
                    "name": "OpenStreetMap (Overpass)",
                    "url": f"https://www.openstreetmap.org/{el.get('type')}/{el.get('id')}",
                    "fetched_at": fetched_at,
                },
            }
        )
    return features


def _fallback_name(kind: str, tags: dict) -> str:
    if kind == "parking":
        variant = tags.get("parking", "")
        return f"{variant.replace('_', ' ').title()} parking".strip().capitalize()
    if kind == "roadwork":
        return f"Road under construction ({tags.get('construction', 'works')})"
    if kind == "construction":
        return "Construction site"
    return (tags.get("amenity") or tags.get("leisure") or "Venue").replace("_", " ").title()
