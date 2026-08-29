"""
In-process smoke test for the Know Ahead backend.

Drives the FastAPI app directly via TestClient — no running server, no network,
no frontend. Exercises the full pipeline (sources -> change detection -> geo
filter -> impact scoring -> deterministic summary) through the real HTTP routes.

Run:
    cd backend
    ../.venv/Scripts/python.exe smoke_test.py        # Windows
    ../.venv/bin/python smoke_test.py                 # macOS/Linux

Exits 0 on success, 1 on the first failed assertion.

Note: this wipes backend/data/{locations,last_snapshot,pulse,seed_planning_events}.json
at the start so every run is identical. Don't point it at data you care about.
"""

from __future__ import annotations

import os
import sys

# This test asserts the *deterministic* pipeline contract, so pin the LLM off
# before config/main import — even if .env has USE_LLM=1. load_dotenv() won't
# override an env var that's already set.
os.environ["USE_LLM"] = "0"

from fastapi.testclient import TestClient

import config
from main import app

assert config.USE_LLM is False, "smoke test must run with USE_LLM off"

client = TestClient(app)

# A plausible Sydney home ~140 m from the seeded development approval.
HOME = {
    "label": "Home",
    "address": "Redfern NSW 2016",
    "latitude": -33.8846,
    "longitude": 151.2020,
    "lease_end_date": "2027-01-15",
    "works_from_home": True,
}

_passed = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global _passed
    mark = "PASS" if condition else "FAIL"
    print(f"  [{mark}] {label}" + (f"  -- {detail}" if detail else ""))
    if not condition:
        raise AssertionError(label)
    _passed += 1


def reset_state() -> None:
    for path in (
        config.LOCATIONS_FILE,
        config.SNAPSHOT_FILE,
        config.PULSE_FILE,
        config.SEED_EVENTS_FILE,
    ):
        path.unlink(missing_ok=True)


def main() -> int:
    reset_state()

    print("health")
    r = client.get("/health")
    check("GET /health -> 200", r.status_code == 200)
    check("status is ok", r.json().get("status") == "ok")
    check("reports llm flag", "llm" in r.json(), str(r.json().get("llm")))

    print("locations")
    r = client.post("/locations", json=HOME)
    check("POST /locations -> 200", r.status_code == 200)
    location = r.json()
    location_id = location["id"]
    check("response has an id", bool(location_id), location_id)
    check("fields round-trip", location["label"] == "Home" and location["works_from_home"] is True)

    r = client.get("/locations")
    check("GET /locations lists it", any(loc["id"] == location_id for loc in r.json()))

    print("monitor (first run — should detect the seeded approval)")
    client.post("/demo/reset")
    r = client.get(f"/monitor/{location_id}")
    check("GET /monitor/{id} -> 200", r.status_code == 200)
    result = r.json()
    check("exactly one change detected", len(result["changes"]) == 1, f"{len(result['changes'])} changes")

    change = result["changes"][0]
    check("change is 'new'", change["change_type"] == "new", change["change_type"])
    check("distance is within the relevance radius",
          change["distance_m"] <= config.RELEVANCE_RADIUS_M, f"{round(change['distance_m'])} m")
    check("impact is scored", set(change["impact"]) >= {"noise", "traffic", "dust"})
    check("explanation mentions the distance and the location label",
          "Home" in result["explanation"] and "m from" in result["explanation"],
          result["explanation"])
    check("recommendation flags the lease overlap",
          "lease" in result["recommendation"].lower(), result["recommendation"])

    print("monitor (second run — snapshot consumed, nothing new)")
    r = client.get(f"/monitor/{location_id}")
    check("no changes on the second run", r.json()["changes"] == [])

    print("decision mode (ad-hoc address, no saved location)")
    client.post("/demo/reset")
    r = client.post("/decision", json={
        "address": "1 Example St, Redfern NSW",
        "latitude": HOME["latitude"],
        "longitude": HOME["longitude"],
        "question": "Should I renew my lease?",
        "lease_end_date": "2027-01-15",
    })
    check("POST /decision -> 200", r.status_code == 200)
    decision = r.json()
    check("echoes the question", "Should I renew my lease?" in decision["explanation"])
    check("finds the same nearby change", len(decision["changes"]) == 1)

    print("404s")
    check("unknown location -> 404", client.get("/monitor/does-not-exist").status_code == 404)

    print("pulse (background monitor is off by default)")
    r = client.get(f"/pulse/{location_id}")
    check("GET /pulse/{id} -> 200", r.status_code == 200)
    check("reports no pulse yet", "status" in r.json())

    return 0


if __name__ == "__main__":
    try:
        rc = main()
    except AssertionError as exc:
        print(f"\nFAILED: {exc}")
        sys.exit(1)
    print(f"\nAll {_passed} checks passed.")
    sys.exit(rc)
