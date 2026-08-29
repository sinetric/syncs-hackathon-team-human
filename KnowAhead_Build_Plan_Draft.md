# Know Ahead — Hackathon Build Plan

**Goal:** one polished end-to-end flow. A Marrickville resident opens the app → sees a *new* development approval detected near their home → gets a personalised impact read → asks "Should I renew my lease?" → gets an evidence-based recommendation.

**Locked decisions:** FastAPI backend · React + Vite + Leaflet frontend · Marrickville hero location · JSON/SQLite for state (no Postgres) · four builders.

---

## 1. The contract: `UrbanEvent` schema

Agree this in the first 30 minutes. It's the interface between all four workstreams — once it's fixed, everyone builds in parallel against it without blocking.

```json
{
  "id": "da-2025-1234",
  "type": "development | roadwork | incident | flood | event | weather",
  "title": "Demolition and construction of 4-storey residential flat building",
  "description": "…source text, trimmed…",
  "latitude": -33.9106,
  "longitude": 151.1547,
  "start_date": "2025-08-20",
  "end_date": "2027-02-20",
  "source": "NSW Planning Portal | TfNSW Live Traffic | OpenWeather",
  "status": "approved | active | scheduled | cancelled",
  "last_updated": "2026-08-29T09:00:00Z",

  "detected_at": "2026-08-29T09:00:00Z",   // set by change-detection, not the source
  "distance_m": 180,                          // computed by backend, NOT the LLM
  "impact": null                              // filled by /analyze
}
```

`distance_m`, dates, and coordinates are **facts computed by code**. The LLM never recomputes them — it only reasons over them. This is the single most important design rule in the whole project.

---

## 2. Backend: three endpoints (FastAPI)

| Endpoint | Does |
|---|---|
| `POST /ingest` | Pull all feeds → normalise to `UrbanEvent[]` → write `snapshot_t0.json`. Run once to seed "yesterday". |
| `POST /refresh` | Pull again → diff against last snapshot → return events where `id` is new (or status/date changed). This *is* change detection. |
| `POST /analyze` | Take the new/nearby events + user context → Haversine distance filter → one Claude call → return impact + explanation + recommendation JSON. |

State = two JSON files on disk. The diff is `set(new_ids) - set(old_ids)` plus a shallow field compare. That's the feature, not a shortcut.

---

## 3. Data sources & the change-detection trick

**TfNSW Live Traffic Hazards** — one GeoJSON feed covering roadworks + incidents + floods + major events, with coordinates. Try the keyless mirrors first:
- `https://data.livetraffic.com/traffic/hazards/roadwork.json`
- `.../incident.json` · `.../flood.json` · major events
- If gated: register free at `opendata.transport.nsw.gov.au` for a key and use `https://api.transport.nsw.gov.au/v1/live/hazards/...`.

Filter to a radius/bounding box around Marrickville (≈ `-33.911, 151.155`).

**Development approvals** — the NSW Planning Portal DA API needs an email-requested key that won't arrive during the event, so **hand-curate ~10 real recent Marrickville DAs** into `seed_da.json` from the Planning Portal DA tracker. **Hold 2 back.**

**Weather** — OpenWeather (instant key). Optional; only wire it if you have time after the core flow works.

### The trick that makes change detection demoable
You have no real "yesterday," and nothing convenient will change live during the demo. So control the timeline:
- **DA hero beat (scripted):** seed the snapshot *without* the 2 held-back DAs. On stage, hit `/refresh` → they surface as **new** → the alert fires on cue. The diff logic is 100% real; you're just controlling when the delta appears.
- **Hazards beat (genuinely live):** the TfNSW feed actually changes through the day, so a roadwork/incident diff can be real and unscripted — a nice honest counterpoint to the scripted DA reveal.

---

## 4. Four-person split

Kick off together, lock the schema, then:

**① Data / ingest** — TfNSW feed flowing + normalise → `UrbanEvent`; curate `seed_da.json` (hold 2 back); own `/ingest`, `/refresh`, and the diff.

**② Backend / logic** — Haversine distance filter, impact-scoring stub, and the `/analyze` Claude call (prompt in §6). Works against fake events until ① lands real ones.

**③ Frontend / map** — Leaflet map (home marker, event markers, distance rings), the "Pulse" alert-card list, the event detail panel. Wires to mocked JSON first.

**④ Experience + pitch** — owns the *aha*: proactive alert banner + Decision Mode ("Should I renew my lease?"), visual polish, demo script, slides. Floats as integrator (needs everything working, so pushes integration).

Everyone codes against the §1 schema, so ①–③ never block each other.

---

## 5. Timeline — build the demo *backwards*

The classic failure is bottom-up with nothing to show at hour 20. Instead, get a **fake** end-to-end slice working first, then swap real parts in behind it. You stay demoable at every checkpoint.

| Hours | Focus | Checkpoint |
|---|---|---|
| 0 – 0.5 | Kickoff, lock schema, repo scaffold, assign owners | — |
| 0.5 – 4 | **Fake vertical slice:** hardcoded home + 1 hardcoded "new" DA → real `/analyze` call → map renders marker + alert banner | ✅ Demoable #1 |
| 4 – 10 | Real data: TfNSW live + DA seed + normalise + diff; real Haversine; real map (rings, Pulse, detail) | — |
| 10 – 14 | Integration — swap fake for real behind the same UI | ✅ Demoable #2 (real E2E) |
| 14 – 18 | Decision Mode + proactive alert polish + wire the seeded DA reveal | — |
| 18 – 21 | Polish, error handling (feeds *will* flake — cache last good snapshot), visual pass | — |
| 21 – 23 | Rehearse demo, slides, **code freeze** | — |
| 23 – 24 | Buffer + final rehearsal | 🚫 no new features after H21 |

---

## 6. The `/analyze` Claude prompt

Default model: `claude-sonnet-5` (smart enough for the reasoning, fast enough for a live refresh; drop to `claude-haiku-4-5` if you need more speed on stage). Send the system prompt once, put the filled user template in `messages`, request JSON-only, and parse defensively (strip ``` fences just in case).

### System prompt

```
You are the reasoning layer of Know Ahead, a personal urban intelligence assistant for
Sydney residents.

You receive: (1) a user's saved location and personal context, and (2) a list of nearby
urban events already verified and geolocated by upstream code. Distances, dates, and
coordinates are facts computed deterministically — treat them as ground truth. Never
recompute or contradict them, and never invent events, developments, dates, or distances
that are not in the input.

Your job is to interpret these verified facts for THIS specific person: assess likely
impact, explain it in plain English, and suggest what they should consider doing. You do
not establish facts; you reason over them.

Rules:
- Only reason from the events provided.
- Label the certainty of every claim as one of:
    "known"     — stated directly in the event data (e.g. a DA was lodged).
    "inferred"  — a reasonable consequence of a known fact (e.g. construction may raise noise).
    "predicted" — a forward-looking overlap/effect (e.g. this may coincide with the lease).
- Never present inferred or predicted claims as guaranteed. Prefer "may", "likely", "could".
- Rate each impact factor as "high", "medium", "low", or "none", weighing event type,
  proximity, duration, and the user's stated exposure (e.g. works-from-home → weight noise higher).
- Tie every recommendation to the specific event(s) that motivate it.
- Help the user decide; never decide for them.
- Output ONLY valid JSON matching the schema. No markdown, no code fences, no preamble.

Output schema:
{
  "headline": "one short proactive-alert line",
  "events": [
    {
      "event_id": "string",
      "summary": "one plain-English sentence on what changed",
      "distance_m": number,
      "impacts": [ { "factor": "noise|traffic|dust|access|safety|…",
                     "rating": "high|medium|low|none",
                     "basis": "known|inferred|predicted" } ],
      "why_it_matters": "ties to the user's context",
      "recommendation": "clear, actionable, cautious",
      "confidence": "high|medium|low",
      "evidence": ["short factual bullets tracing the reasoning"]
    }
  ],
  "decision_answer": "answer if the user asked a decision question, else null"
}
```

### User message template (backend fills this)

```
USER CONTEXT
- Saved location: Home — Marrickville NSW (-33.911, 151.155)
- Situation: considering renewing a 12-month lease; current lease expires in ~2 months
- Work pattern: works from home most days
- Question (optional): "Should I renew my lease?"

NEARBY EVENTS (verified, newest first)
<insert UrbanEvent[] JSON here, distances already computed>

Analyze these events for this person. Return JSON per the schema.
```

The persona above (works-from-home, lease expiring in 2 months) is the demo user — it's what makes the "high noise + lease overlap" read land. Swap it freely; it's just the context object.

---

## 7. Demo script (~75 seconds)

1. "This is Sarah's home in Marrickville." — map with home marker, calm state.
2. "Know Ahead watches the places that matter. Watch what happens when it re-scans." — hit **refresh**.
3. 🚨 banner: **"Something changed 180m from your home."** — new DA marker + distance ring appear.
4. Open the card: what changed, where, how long, impact ratings (Noise 🔴 / Traffic 🟠 / Dust 🟡), confidence.
5. "Sarah's lease is up in two months. So she asks Know Ahead directly." — **Decision Mode:** "Should I renew my lease?"
6. Response: *"This construction is likely to overlap with your next lease. Investigate permitted construction hours before renewing."*
7. Close on the line: **"AI answers questions. Know Ahead watches for the questions you didn't know to ask."**

---

## 8. Guardrails — what NOT to build

- ❌ PostGIS / Postgres — Haversine in Python is enough.
- ❌ Auth, accounts, user management.
- ❌ Multiple real locations — one real Home; fake a second marker in the UI if you want texture.
- ❌ Real prediction ML — "overlap" reasoning from dates is your prediction.
- ❌ All five sources fully — TfNSW + DA seed carries the demo.
- ❌ Any new feature after H21.

> The hackathon goal isn't to handle every urban signal. It's to prove: **fragmented city data can become proactive, personalised urban intelligence.**
