"""
Contract smoke test — hits every docs/api-contract.md endpoint in DEMO_MODE
and asserts the response shapes. Run from backend/:

    python smoke_test_v1.py        (or: pytest smoke_test_v1.py)

Fully offline: DEMO_MODE is forced on before the app is imported.
"""

from __future__ import annotations

import os

os.environ["DEMO_MODE"] = "true"

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

client = TestClient(app)

ALERT_KEYS = {
    "id", "kind", "severity", "title", "body", "impact", "affects",
    "valid_from", "valid_to", "geo", "actions", "source",
}


def test_health():
    body = client.get("/api/v1/health").json()
    assert body["status"] == "ok"
    assert body["demo_mode"] is True
    assert "version" in body


def test_demo_seed():
    body = client.post("/api/v1/demo/seed").json()
    assert body["places"] == 2
    assert body["routines"] == 1


def test_places_crud():
    created = client.post(
        "/api/v1/places",
        json={"label": "Gym", "address": "1 Test St, Sydney NSW", "lat": -33.88, "lng": 151.20},
    )
    assert created.status_code == 201
    place = created.json()
    assert place["id"].startswith("plc_") and place["label"] == "Gym"

    listed = client.get("/api/v1/places").json()
    assert any(p["id"] == place["id"] for p in listed["data"])

    assert client.delete(f"/api/v1/places/{place['id']}").status_code == 204
    missing = client.delete(f"/api/v1/places/{place['id']}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "place_not_found"


def test_routines():
    client.post("/api/v1/demo/seed")
    places = client.get("/api/v1/places").json()["data"]
    created = client.post(
        "/api/v1/routines",
        json={
            "name": "Evening return", "origin_id": places[1]["id"], "dest_id": places[0]["id"],
            "days": ["mon", "wed"], "depart_local_time": "17:30", "mode": "transit",
        },
    )
    assert created.status_code == 201
    assert created.json()["id"].startswith("rtn_")

    bad = client.post(
        "/api/v1/routines",
        json={
            "name": "Broken", "origin_id": "plc_nope", "dest_id": places[0]["id"],
            "days": ["mon"], "depart_local_time": "09:00", "mode": "walk",
        },
    )
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "unknown_origin"


def test_alerts():
    client.post("/api/v1/demo/seed")
    body = client.get("/api/v1/alerts", params={"window_mins": 180}).json()
    alerts = body["data"]
    assert alerts, "demo seed must produce alerts"
    for alert in alerts:
        assert ALERT_KEYS <= set(alert.keys())
        assert alert["severity"] in ("info", "watch", "act")
        assert "+10:00" in alert["valid_from"] or "+11:00" in alert["valid_from"]
    assert any(a["severity"] == "act" for a in alerts), "demo must show an act alert"
    assert any(a["kind"] == "reminder" for a in alerts), "demo must show a leave-now reminder"

    routines = client.get("/api/v1/routines").json()["data"]
    scoped = client.get("/api/v1/alerts", params={"routine_id": routines[0]["id"]}).json()
    for alert in scoped["data"]:
        assert routines[0]["id"] in alert["affects"]["routine_ids"]


def test_journey_preview():
    client.post("/api/v1/demo/seed")
    places = {p["label"]: p for p in client.get("/api/v1/places").json()["data"]}
    preview = client.get(
        "/api/v1/journeys/preview",
        params={"origin_id": places["Home"]["id"], "dest_id": places["Uni"]["id"], "mode": "transit"},
    ).json()
    assert preview["trip_mode"] in ("long", "short")
    assert preview["legs"], "must return legs"
    for i, leg in enumerate(preview["legs"]):
        assert leg["index"] == i
        assert {"mode", "from", "to", "depart_at", "arrive_at", "line", "duration_minutes"} <= set(leg)
    assert preview["fare"]["currency"] == "AUD"
    assert preview["fare"]["basis"].startswith("opal")
    assert preview["trip_mode"] == "long", "demo transit journey should be a long trip"
    assert preview["checklist"], "long trip must carry a checklist"

    missing = client.get(
        "/api/v1/journeys/preview",
        params={"origin_id": "plc_nope", "dest_id": places["Uni"]["id"]},
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "place_not_found"


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL  {name}: {exc}")
    raise SystemExit(1 if failures else 0)
