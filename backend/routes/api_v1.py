"""
/api/v1 — the contract surface (docs/api-contract.md).

Every list endpoint returns { "data": [...] }; every error returns
{ "error": { "code", "message" } } via the handlers installed in main.py.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, Response

from pydantic import BaseModel, Field

from config import APP_VERSION, DEMO_MODE
from alerts import build_alerts
from geo import haversine_m
from journeys import build_preview
from models import Severity
from services import ai as ai_service
from services.overpass import ALL_KINDS, fetch_features
from services.parking import find_parking
from services.weather import get_weather
from models import (
    Place,
    PlaceCreate,
    Routine,
    RoutineCreate,
    TravelMode,
    Weekday,
)
from store import (
    get_place,
    load_places,
    load_routines,
    save_places,
    save_routines,
)
from timeutil import now_syd, parse_iso_syd

router = APIRouter(prefix="/api/v1", tags=["v1"])


def _err(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


# ---------------------------------------------------------------------- meta


@router.get("/health")
def health():
    return {"status": "ok", "version": APP_VERSION, "demo_mode": DEMO_MODE}


# -------------------------------------------------------------------- places


@router.get("/places")
def list_places():
    return {"data": [p.model_dump(mode="json") for p in load_places()]}


@router.post("/places", status_code=201)
def create_place(payload: PlaceCreate):
    places = load_places()
    place = Place(**payload.model_dump())
    places.append(place)
    save_places(places)
    return place.model_dump(mode="json")


@router.delete("/places/{place_id}", status_code=204)
def delete_place(place_id: str):
    places = load_places()
    remaining = [p for p in places if p.id != place_id]
    if len(remaining) == len(places):
        raise _err(404, "place_not_found", "No place with that id.")
    save_places(remaining)
    # routines pointing at a deleted place are removed too — a routine
    # without both endpoints can never produce a journey or an alert
    routines = [
        r for r in load_routines()
        if r.origin_id != place_id and r.dest_id != place_id
    ]
    save_routines(routines)
    return Response(status_code=204)


# ------------------------------------------------------------------ routines


@router.get("/routines")
def list_routines():
    return {"data": [r.model_dump(mode="json") for r in load_routines()]}


@router.post("/routines", status_code=201)
def create_routine(payload: RoutineCreate):
    if get_place(payload.origin_id) is None:
        raise _err(422, "unknown_origin", "origin_id does not match a saved place.")
    if get_place(payload.dest_id) is None:
        raise _err(422, "unknown_destination", "dest_id does not match a saved place.")
    if payload.origin_id == payload.dest_id:
        raise _err(422, "same_place", "Origin and destination must differ.")
    routines = load_routines()
    routine = Routine(**payload.model_dump())
    routines.append(routine)
    save_routines(routines)
    return routine.model_dump(mode="json")


# -------------------------------------------------------------------- alerts


@router.get("/alerts")
def list_alerts(
    routine_id: str | None = Query(default=None),
    place_id: str | None = Query(default=None),
    window_mins: int = Query(default=180, ge=15, le=1440 * 3),
):
    alerts = build_alerts(routine_id=routine_id, place_id=place_id, window_mins=window_mins)
    return {"data": [a.model_dump(mode="json", by_alias=True) for a in alerts]}


# ------------------------------------------------------------------ journeys


@router.get("/journeys/preview")
def journey_preview(
    origin_id: str,
    dest_id: str,
    depart_at: str | None = Query(default=None),
    mode: TravelMode = Query(default=TravelMode.transit),
):
    origin = get_place(origin_id)
    dest = get_place(dest_id)
    if origin is None:
        raise _err(404, "place_not_found", "origin_id does not match a saved place.")
    if dest is None:
        raise _err(404, "place_not_found", "dest_id does not match a saved place.")
    if depart_at is None:
        when = now_syd()
    else:
        try:
            when = parse_iso_syd(depart_at)
        except ValueError:
            raise _err(422, "bad_depart_at", "depart_at must be an ISO 8601 datetime.")
    preview = build_preview(origin, dest, when, mode)
    return preview.model_dump(mode="json", by_alias=True)


# ----------------------------------------------------------- map / live data


@router.get("/map/features")
def map_features(
    lat: float = Query(ge=-90, le=90),
    lng: float = Query(ge=-180, le=180),
    radius_m: int = Query(default=1500, ge=200, le=5000),
    kinds: str | None = Query(default=None, description="csv of feature kinds"),
):
    """Real mapped objects (OSM via Overpass) merged with the alert engine's
    geo-located events, for the interactive map."""
    kind_list = [k.strip() for k in kinds.split(",")] if kinds else None
    osm_kinds = [k for k in (kind_list or ALL_KINDS) if k in ALL_KINDS]
    features, overpass_ok = fetch_features(lat, lng, radius_m, osm_kinds)

    alert_features = []
    for alert in build_alerts(window_mins=720):
        if alert.geo is None:
            continue
        if haversine_m(lat, lng, alert.geo.lat, alert.geo.lng) > radius_m:
            continue
        if kind_list and alert.kind.value not in kind_list:
            continue
        alert_features.append(
            {
                "id": alert.id,
                "kind": alert.kind.value,
                "name": alert.title,
                "lat": alert.geo.lat,
                "lng": alert.geo.lng,
                "tags": {},
                "alert": alert.model_dump(mode="json"),
                "source": alert.source.model_dump(mode="json"),
            }
        )

    return {
        "data": alert_features + features,
        "overpass_available": overpass_ok,
        "fetched_at": now_syd().isoformat(),
    }


@router.get("/weather")
def weather(
    lat: float = Query(ge=-90, le=90),
    lng: float = Query(ge=-180, le=180),
):
    result, available = get_weather(lat, lng)
    if not available:
        raise _err(503, "weather_unavailable", "Open-Meteo could not be reached.")
    return result


@router.get("/parking")
def parking(
    lat: float = Query(ge=-90, le=90),
    lng: float = Query(ge=-180, le=180),
    radius_m: int = Query(default=1200, ge=200, le=5000),
):
    weather_data, weather_ok = get_weather(lat, lng)
    raining = bool(weather_data["derived"]["raining_now"]) if weather_ok else False
    event_count = sum(
        1 for a in build_alerts(window_mins=360)
        if a.severity != Severity.info and a.geo is not None
        and haversine_m(lat, lng, a.geo.lat, a.geo.lng) <= radius_m + 1000
    )
    spots, available = find_parking(lat, lng, radius_m, now_syd(), event_count, raining)
    if not available:
        raise _err(503, "parking_unavailable", "OpenStreetMap (Overpass) could not be reached.")
    return {"data": spots, "fetched_at": now_syd().isoformat()}


# ------------------------------------------------------------------- ask AI


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    origin_id: str | None = None
    dest_id: str | None = None


@router.post("/ask")
def ask_ai(payload: AskRequest):
    return ai_service.ask(payload.question, payload.origin_id, payload.dest_id)


# ---------------------------------------------------------------------- demo


@router.post("/demo/seed")
def demo_seed():
    """Load the demo fixtures: two places and one routine. The routine's next
    departure is set ~45 minutes from now so the leave-now reminder and the
    'act' disruption always land in the default alert window."""
    home = Place(label="Home", address="12 Illawarra Rd, Marrickville NSW",
                 lat=-33.9110, lng=151.1554)
    uni = Place(label="Uni", address="15 Broadway, Ultimo NSW",
                lat=-33.8836, lng=151.1997)
    save_places([home, uni])

    depart = (now_syd() + timedelta(minutes=45)).strftime("%H:%M")
    routine = Routine(
        name="Uni run",
        origin_id=home.id,
        dest_id=uni.id,
        days=[Weekday.mon, Weekday.tue, Weekday.wed, Weekday.thu,
              Weekday.fri, Weekday.sat, Weekday.sun],
        depart_local_time=depart,
        mode=TravelMode.transit,
    )
    save_routines([routine])
    return {"places": 2, "routines": 1, "depart_local_time": depart}
