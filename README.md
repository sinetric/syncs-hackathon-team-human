# Know Ahead

Know Ahead is destination-agnostic. It doesn't answer "how do I get there" —
it answers **"what changed since last time that you'd have wanted to know
before you left."** Saved places and routines in, ranked heads-up alerts out:
transport disruptions, roadworks, rain, construction near home — plus a
leave-now reminder computed from your routine and the live delay.

Frontend (React + Vite + TS + Tailwind) and backend (FastAPI) talk only
through [docs/api-contract.md](docs/api-contract.md).

## Quickstart (5 commands, works fully offline)

```bash
git clone https://github.com/sinetric/syncs-hackathon-team-human.git && cd syncs-hackathon-team-human
python -m venv backend/.venv && backend\.venv\Scripts\pip install -r backend/requirements.txt
npm install && npm --prefix frontend install
backend\.venv\Scripts\activate
npm run dev
```

Backend on http://localhost:8000 (docs at `/docs`), frontend on
http://localhost:5173 (or the next free port — check the terminal).
On macOS/Linux use `source backend/.venv/bin/activate` instead of line 4.

Then in the app: open **Today** and tap **Load demo data** (or
`curl -X POST http://localhost:8000/api/v1/demo/seed`). You'll get two places,
one routine departing ~45 min from now, an "act" disruption, a live countdown,
and a 74-minute journey preview with a checklist.

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
| `SOURCE_CACHE_TTL_S` | backend | `120` | per-source raw-response cache |
| `CORRIDOR_RADIUS_M` | backend | `800` | route-corridor match radius |
| `CORS_ORIGINS` | backend | `*` | comma-separated origins |
| `VITE_API_BASE_URL` | frontend | `http://localhost:8000` | backend origin |
| `VITE_USE_FIXTURES` | frontend | `false` | UI-only offline mode |

Live Traffic NSW and Open-Meteo need no keys.

## Tests

```bash
npm run smoke
```

Hits every contract endpoint in DEMO_MODE and asserts response shapes.

## Architecture

```
backend/
  routes/api_v1.py     the /api/v1 contract surface
  alerts/              the alert engine: adapters -> dedupe -> matcher -> scorer
    adapters/          TfNSW, Live Traffic NSW, Open-Meteo, NSW Planning —
                       one file each, all emitting a normalised SourceEvent;
                       a dead source degrades to empty, never a 500
  journeys.py          legs, Opal fare-band estimate, checklist rules
  fixtures/            demo-mode data
frontend/
  src/api/             typed client + contract types + offline fixtures
  src/screens/         Today / Journey / Places / More
```

Known v1 limits (deliberate): the corridor matcher samples the straight line
between origin and destination rather than real route geometry; fares are a
static Opal band table labelled as estimates; the demo transit itinerary is a
fixture. The NSW Planning live API needs an emailed subscription key, so both
modes currently read seed data for that source.
