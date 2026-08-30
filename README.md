# Know Ahead

Your day runs on public information you rarely think to look up — whether a
train line is running late, which street was dug up overnight, if rain lands
mid-commute, whether a build site is going up next to home, which roads close
for a weekend event. All of it is published somewhere, and most people find
out only once it has already cost them time.

Know Ahead bridges that gap. It watches those sources around the places and
routines you actually use and surfaces the handful that matter as ranked
heads-up alerts: transport disruptions, roadworks, weather, nearby
construction — plus a leave-now reminder computed from your routine and the
live delay. You hand it saved places and routines; it keeps watch on the
public record for you, so the thing you'd have wanted to know reaches you
before you leave rather than after.

On top of the alert feed sit four live-data surfaces:

- **Map** — real OpenStreetMap objects (parking, construction, roadworks,
  event venues via Overpass) merged with the alert engine's geo events, with
  per-type icons, filters, a legend, a radius selector, and 60-second refresh.
- **Journey map** — origin/destination markers, a dashed visual connection
  (deliberately not a navigation route), obstacles near the corridor, live
  weather at the destination, and nearby parking with an *estimated* parking
  probability (heuristic, labelled — no live occupancy source exists).
- **Live weather** — Open-Meteo, fetched live even in demo mode, feeding the
  alert engine, journey checklist and AI answers; observed values and derived
  interpretations are kept strictly separate.
- **Ask AI** — questions answered from the app's own live context (alerts,
  weather, journey, parking) by Qwen — hosted via Hugging Face when
  `HF_TOKEN` is set, local `transformers` Qwen when `USE_LLM=1` — with a
  clearly-labelled rule-based fallback when no model is available. Every
  answer lists the factors behind it and which engine produced it.

Frontend (React + Vite + TypeScript + Tailwind) and backend (FastAPI) talk
only through [docs/api-contract.md](docs/api-contract.md).

## Prerequisites

- **Python 3.11+** (developed on 3.14)
- **Node.js 18+** and npm
- No API keys — demo mode works fully offline

## Setup

Clone, create the backend virtualenv, then install both dependency sets.

**Windows (PowerShell)**

```powershell
git clone https://github.com/sinetric/syncs-hackathon-team-human.git
cd syncs-hackathon-team-human

python -m venv backend\.venv
backend\.venv\Scripts\pip install -r backend\requirements.txt

npm install                     # root: concurrently, to run both servers
npm --prefix frontend install   # frontend deps
```

**macOS / Linux**

```bash
git clone https://github.com/sinetric/syncs-hackathon-team-human.git
cd syncs-hackathon-team-human

python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt

npm install
npm --prefix frontend install
```

`backend/requirements.txt` includes `transformers` + `torch` for the optional
local Qwen model. That's a large download; for demo mode with the rule-based AI
fallback you can skip it — install just
`fastapi uvicorn[standard] httpx requests pydantic python-dotenv tzdata` and set
`USE_LLM=0`.

## Run it locally

### Both servers at once (recommended)

From the repo root:

```bash
npm run dev
```

`concurrently` starts the API and the web app together and colour-codes their
logs:

- **API** → http://localhost:8000 — Swagger UI at `/docs`, contract under `/api/v1`
- **Web** → http://localhost:5173 — or the next free port; check the terminal

Ctrl+C stops both. (`npm run dev` runs `python main.py` for the backend, so the
`backend/.venv` interpreter must be the one on `PATH` — activate it first, or
run the two servers separately as below.)

### Backend only — uvicorn

Activate the venv, then run uvicorn from `backend/`:

**Windows (PowerShell)**

```powershell
backend\.venv\Scripts\Activate.ps1
cd backend
uvicorn main:app --reload --port 8000
```

**macOS / Linux**

```bash
source backend/.venv/bin/activate
cd backend
uvicorn main:app --reload --port 8000
```

`--reload` restarts on file changes. `python main.py` (from `backend/`) is
equivalent — it just calls `uvicorn.run("main:app", port=8000, reload=True)`.
Without activating the venv, target its interpreter directly:
`backend\.venv\Scripts\python -m uvicorn main:app --reload` (PowerShell) or
`backend/.venv/bin/python -m uvicorn main:app --reload` (macOS / Linux).

### Frontend only — npm run dev

```bash
cd frontend
npm run dev
```

Vite serves http://localhost:5173 and calls the API at `VITE_API_BASE_URL`
(default `http://localhost:8000`). Run the backend separately, or set
`VITE_USE_FIXTURES=true` in `frontend/.env` to render the whole UI from local
fixtures with no backend at all.

### Load demo data

With both servers up, open **Today** and tap **Load demo data**, or:

```bash
curl -X POST http://localhost:8000/api/v1/demo/seed
```

You get two places, a routine departing ~45 min from now, an "act" disruption,
a live countdown, and a ~74-minute journey preview with a checklist.

## Demo mode (default)

`DEMO_MODE=true` (the default) serves every data source from
`backend/fixtures/*.json` — realistic Sydney data with validity relative to
"now", so the demo works on any day with the network off. No API keys needed.

For live data, copy `backend/.env.example` to `backend/.env`, set
`DEMO_MODE=false` and add keys. The backend fails loudly at boot if a required
key is missing. If the venue wifi dies entirely, set `VITE_USE_FIXTURES=true`
in `frontend/.env` and the UI renders from local fixtures with no backend.

## Environment variables

| Variable | Where | Default | Notes |
|---|---|---|---|
| `DEMO_MODE` | backend | `true` | fixtures instead of live sources |
| `TFNSW_API_KEY` | backend | — | required only when `DEMO_MODE=false`; free at [opendata.transport.nsw.gov.au](https://opendata.transport.nsw.gov.au) |
| `HF_TOKEN` | backend | — | optional; enables hosted Qwen for Ask AI ([huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)), server-side only; grant Inference Providers access |
| `USE_LLM` | backend | `1` | local Hugging Face Qwen fallback; set `0` to disable it (first use downloads model weights; CPU answers can take minutes) |
| `LLM_MODEL_ID` | backend | `Qwen/Qwen2.5-0.5B-Instruct` | any HF causal-LM id; bump to `Qwen/Qwen2.5-1.5B-Instruct` for better wording |
| `SOURCE_CACHE_TTL_S` | backend | `120` | per-source raw-response cache |
| `GEOCODE_CACHE_TTL_S` | backend | `86400` | address lookup cache; public Nominatim is queried only on Save and must follow its usage policy |
| `CORRIDOR_RADIUS_M` | backend | `800` | route-corridor match radius |
| `CORS_ORIGINS` | backend | `*` | comma-separated origins |
| `VITE_API_BASE_URL` | frontend | `http://localhost:8000` | backend origin (no trailing slash) |
| `VITE_USE_FIXTURES` | frontend | `false` | UI-only offline mode |

Live Traffic NSW and Open-Meteo need no keys.

## Tests

```bash
npm run smoke                              # /api/v1 contract  (backend/smoke_test_v1.py)
backend/.venv/bin/python backend/smoke_test.py   # legacy /monitor pipeline (Windows: backend\.venv\Scripts\python)
```

Both drive the FastAPI app in-process in DEMO_MODE and assert response shapes —
no running server needed. `npm run smoke` uses the `python` on `PATH`, so
activate `backend/.venv` first.

## Architecture

```
backend/
  routes/api_v1.py     the /api/v1 contract surface
  alerts/              the alert engine: adapters -> dedupe -> matcher -> scorer
    adapters/          TfNSW, Live Traffic NSW, Open-Meteo, NSW Planning —
                       one file each, all emitting a normalised SourceEvent;
                       a dead source degrades to empty, never a 500
  services/            live-data services: overpass (OSM, 4-mirror fallback),
                       weather (Open-Meteo, live even in demo mode), parking
                       (OSM + labelled probability heuristic), ai (Qwen with
                       HF-API -> local -> rules engine layering)
  journeys.py          legs, Opal fare-band estimate, checklist rules
  fixtures/            demo-mode data
frontend/
  src/api/             typed client + contract types + offline fixtures
  src/components/      FeatureMap (Leaflet + emoji pins + popup cards), cards
  src/screens/         Today / Map / Journey / Ask / Places
```

Legacy MVP endpoints (`/monitor`, `/decision`, `/locations`, `/pulse`) from an
earlier iteration still mount alongside `/api/v1`, backed by `backend/pipeline/`
and `backend/sources/`. The app and the frontend use `/api/v1` only.

Known v1 limits (deliberate): the corridor matcher samples the straight line
between origin and destination rather than real route geometry; fares are a
static Opal band table labelled as estimates; the demo transit itinerary is a
fixture; parking probability is a heuristic (no live occupancy feed exists);
OSM shows mapped objects, not live traffic. The NSW Planning live API needs
an emailed subscription key, so both modes currently read seed data for that
source. Every estimate is labelled as one in the API and the UI.
