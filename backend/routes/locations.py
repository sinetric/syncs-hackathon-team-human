"""Saved-location CRUD (pitch Section 20 — "My Locations")."""

from __future__ import annotations

from fastapi import APIRouter

from models import SavedLocation, SavedLocationCreate
from store import load_locations, save_locations

router = APIRouter(tags=["locations"])


@router.post("/locations", response_model=SavedLocation)
def create_location(payload: SavedLocationCreate) -> SavedLocation:
    locations = load_locations()
    new_location = SavedLocation(**payload.model_dump())
    locations.append(new_location)
    save_locations(locations)
    return new_location


@router.get("/locations", response_model=list[SavedLocation])
def list_locations() -> list[SavedLocation]:
    return load_locations()
