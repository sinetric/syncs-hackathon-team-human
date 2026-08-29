"""
Normalised internal event — the one shape every source adapter emits.

Adapters do all the upstream-specific parsing; everything downstream
(matcher, scorer, dedupe) only ever sees SourceEvent.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from models import AlertKind


class SourceEvent(BaseModel):
    uid: str                        # "{source}:{external_id}" — dedupe key
    kind: AlertKind
    title: str
    body: str = ""
    lat: float | None = None
    lng: float | None = None
    radius_m: int = 400
    delay_minutes: int | None = None
    lines: list[str] = Field(default_factory=list)   # affected transit lines, e.g. ["T1"]
    valid_from: datetime
    valid_to: datetime
    source_name: str
    source_url: str | None = None
    fetched_at: datetime
    severity_hint: str | None = None                 # adapter may suggest; scorer decides
