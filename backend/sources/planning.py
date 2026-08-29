"""
Planning / development-application source.

Adapter contract: return a list of normalised ``UrbanEvent`` objects.

The NSW Planning Portal's live "Online DA Data API" needs a subscription key
requested by email (not obtainable same-day), so for the hackathon this reads a
local seed file shaped like real DA records. Replace the body of
``fetch_planning_events`` with a real ``requests.get(...)`` call once a key is
issued — nothing downstream needs to change.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from config import SEED_EVENTS_FILE
from models import UrbanEvent


def fetch_planning_events() -> list[UrbanEvent]:
    if not SEED_EVENTS_FILE.exists():
        _write_default_seed()
    raw = json.loads(SEED_EVENTS_FILE.read_text())
    return [UrbanEvent(**item) for item in raw]


def _write_default_seed() -> None:
    """One realistic event ~180 m from a plausible Sydney home address, matching
    the pitch doc's headline demo scenario (Section 32)."""
    seed = [
        {
            "id": "DA-2026-00042",
            "type": "development",
            "title": "Mixed-use residential development — 8 storeys",
            "description": (
                "Demolition of existing structure and construction of an "
                "8-storey mixed-use building with basement parking."
            ),
            "latitude": -33.8845,
            "longitude": 151.2005,
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=18 * 30)),
            "source": "nsw_planning_portal_seed",
            "status": "approved",
            "last_updated": datetime.now().isoformat(),
        }
    ]
    SEED_EVENTS_FILE.write_text(json.dumps(seed, indent=2))
