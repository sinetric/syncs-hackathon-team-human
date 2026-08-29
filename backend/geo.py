"""
geo.py — geospatial helpers.



Works on plain event dicts, matching the
UrbanEvent schema: each event has `latitude` and `longitude` keys.

Typical use in /analyze (depending on AI used):

    from app.geo import filter_by_radius
    home = (-33.911, 151.155)  # Marrickville
    nearby = filter_by_radius(events, home[0], home[1], radius_m=1000)
    # -> events within 1km, each annotated with "distance_m", nearest first
"""

from math import radians, sin, cos, asin, sqrt

EARTH_RADIUS_M = 6_371_000  # Earth radius in metres


def haversine_m(lat1, lon1, lat2, lon2):
    """Great-circle distance between two lat/lng points, in metres."""
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * asin(sqrt(a))


def _coords(event, lat_key, lon_key):
    """Pull (lat, lon) as floats, or None if missing/unparseable.

    callers skip record with no usable coordinates that can't be placed on a map or measured,
    as real feeds have messy records
    """
    try:
        lat = float(event[lat_key])
        lon = float(event[lon_key])
    except (KeyError, TypeError, ValueError):
        return None
    return lat, lon


def annotate_distances(events, origin_lat, origin_lon,
                       lat_key="latitude", lon_key="longitude"):
    """Return copies of events with `distance_m` set (int metres), nearest first.

    Does not mutate the input. Events missing usable coordinates are dropped.
    """
    out = []
    for event in events:
        coords = _coords(event, lat_key, lon_key)
        if coords is None:
            continue
        lat, lon = coords
        dist = round(haversine_m(origin_lat, origin_lon, lat, lon))
        out.append({**event, "distance_m": dist})
    out.sort(key=lambda e: e["distance_m"])
    return out


def filter_by_radius(events, origin_lat, origin_lon, radius_m,
                     lat_key="latitude", lon_key="longitude"):
    """Events within `radius_m` of the origin, annotated with `distance_m`,
    sorted nearest first. This is what /analyze calls before the AI step."""
    annotated = annotate_distances(events, origin_lat, origin_lon, lat_key, lon_key)
    return [e for e in annotated if e["distance_m"] <= radius_m]
