"""Source adapter registry — add an adapter here and it flows through the
whole engine (dedupe -> matcher -> scorer) unchanged."""

from __future__ import annotations

from alerts.adapters.base import SourceAdapter
from alerts.adapters.livetraffic import LiveTrafficAdapter
from alerts.adapters.openmeteo import OpenMeteoAdapter
from alerts.adapters.planning_da import PlanningAdapter
from alerts.adapters.tfnsw import TfnswAdapter

ADAPTERS: list[SourceAdapter] = [
    TfnswAdapter(),
    LiveTrafficAdapter(),
    OpenMeteoAdapter(),
    PlanningAdapter(),
]
