"""Monitoring, decision support, pulse, and demo helpers."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from models import DecisionRequest, MonitorResult, SavedLocation
from pipeline.run import run_pipeline_for_location
from store import clear_snapshot, get_location, load_pulse

router = APIRouter(tags=["monitor"])


@router.get("/monitor/{location_id}", response_model=MonitorResult)
def monitor_location(location_id: str) -> MonitorResult:
    """Pitch Section 5A — run the pipeline now for a saved location."""
    location = get_location(location_id)
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found")
    return run_pipeline_for_location(location)


@router.post("/decision", response_model=MonitorResult)
def decision_mode(payload: DecisionRequest) -> MonitorResult:
    """Pitch Section 6 — "Before You Commit". Ad-hoc address + question, no
    saved location required."""
    ad_hoc = SavedLocation(
        label="this address",
        address=payload.address,
        latitude=payload.latitude,
        longitude=payload.longitude,
        lease_end_date=payload.lease_end_date,
    )
    result = run_pipeline_for_location(ad_hoc)
    if payload.question:
        result.explanation = f"You asked: “{payload.question}”\n\n{result.explanation}"
    return result


@router.get("/pulse/{location_id}")
def get_pulse(location_id: str):
    """Latest proactively-computed result for a location. Populated by the
    background monitor when ENABLE_BACKGROUND_MONITOR=1 (otherwise call
    /monitor/{location_id} directly)."""
    return load_pulse().get(
        location_id,
        {"status": "no pulse yet — call /monitor/{id} or enable the background monitor"},
    )


@router.post("/demo/reset")
def demo_reset():
    """Clear change-detection history so the next /monitor call reports the seed
    event as 'new'. Run this right before a demo."""
    clear_snapshot()
    return {"status": "snapshot cleared"}
