# Know Ahead — API contract (source of truth)

Both the frontend and backend build against this file. Neither side may add,
rename, or remove a field without updating this document first.

Base path: `/api/v1`. All times ISO 8601 with offset (Australia/Sydney).
All list endpoints return `{ "data": [...] }`. All errors return
`{ "error": { "code": "...", "message": "..." } }` with a real HTTP status.

## Endpoints

```
GET    /health                        -> { status, version, demo_mode }
GET    /places                        -> Place[]
POST   /places                        <- { label, address, lat, lng } -> Place
DELETE /places/{id}
GET    /routines                      -> Routine[]
POST   /routines                      <- { name, origin_id, dest_id, days, depart_local_time, mode }
GET    /alerts?routine_id=&place_id=&window_mins=180   -> Alert[]
GET    /journeys/preview?origin_id=&dest_id=&depart_at=&mode=  -> JourneyPreview
POST   /demo/seed                     -> seeds fixtures, returns counts
```

## Objects

```jsonc
// Place
{ "id": "plc_...", "label": "Uni", "address": "15 Broadway, Ultimo NSW",
  "lat": -33.8836, "lng": 151.1997 }

// Routine
{ "id": "rtn_...", "name": "Uni run", "origin_id": "plc_...", "dest_id": "plc_...",
  "days": ["mon","tue","wed","thu","fri"], "depart_local_time": "07:40",
  "mode": "transit" }            // transit | drive | walk

// Alert  — the core object; the whole UI is a list of these
{ "id": "alt_...",
  "kind": "transport_disruption",   // transport_disruption | roadwork | incident
                                    // | weather | construction | reminder | advice
  "severity": "act",                // info | watch | act
  "title": "T1 trains delayed up to 12 min",
  "body": "Signal fault at Strathfield. Affects your 07:40 uni run.",
  "impact": { "delay_minutes": 12, "confidence": 0.72 },
  "affects": { "routine_ids": ["rtn_..."], "place_ids": [], "leg_index": 1 },
  "valid_from": "2026-08-29T06:00:00+10:00",
  "valid_to":   "2026-08-29T11:00:00+10:00",
  "geo": { "lat": -33.87, "lng": 151.09, "radius_m": 400 },
  "actions": [ { "type": "leave_earlier", "label": "Leave 12 min earlier",
                 "payload": { "minutes": 12 } },
               { "type": "reroute", "label": "Show alternative" } ],
  "source": { "name": "Transport for NSW", "url": "https://...",
              "fetched_at": "2026-08-29T06:02:11+10:00" } }

// JourneyPreview
{ "duration_minutes": 74, "trip_mode": "long",   // long if > 60 min, else short
  "legs": [ { "index": 0, "mode": "walk", "from": "Home", "to": "Wiley Park",
              "depart_at": "...", "arrive_at": "...", "line": null,
              "duration_minutes": 8 } ],
  "fare": { "currency": "AUD", "estimate_cents": 452, "basis": "opal_adult_offpeak" },
  "checklist": [ { "id": "chk_water", "label": "Water bottle", "reason": "74 min trip" } ],
  "alerts": [ /* Alert[] scoped to this journey */ ] }
```

## Severity rules

The backend owns severity; the frontend never recomputes it.

- `act` — the user must change behaviour now (leave earlier, reroute).
- `watch` — will matter within the window but no action yet.
- `info` — context only (construction near home, rain later).
