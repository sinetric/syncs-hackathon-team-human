"""
Central configuration — file paths and tunables for the Know Ahead backend.

Flat JSON files are fine for a 24h MVP; swap `store.py` for a real DB later
without changing anything here.
"""

from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).parent

# Load backend/.env if python-dotenv is installed (optional — the defaults below
# work with no .env present).
try:  # pragma: no cover - convenience only
    from dotenv import load_dotenv

    load_dotenv(BACKEND_DIR / ".env")
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Storage paths
# ---------------------------------------------------------------------------

DATA_DIR = BACKEND_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

LOCATIONS_FILE = DATA_DIR / "locations.json"
SNAPSHOT_FILE = DATA_DIR / "last_snapshot.json"          # for change detection
PULSE_FILE = DATA_DIR / "pulse.json"                     # latest proactive result per location
SEED_EVENTS_FILE = DATA_DIR / "seed_planning_events.json"

# v1 contract storage (docs/api-contract.md)
PLACES_FILE = DATA_DIR / "places.json"
ROUTINES_FILE = DATA_DIR / "routines.json"
DISMISSED_FILE = DATA_DIR / "dismissed_alerts.json"

FIXTURES_DIR = BACKEND_DIR / "fixtures"

# ---------------------------------------------------------------------------
# v1 API (docs/api-contract.md)
# ---------------------------------------------------------------------------

APP_VERSION = "0.2.0"
APP_TZ = "Australia/Sydney"

# DEMO_MODE=true serves every source adapter from fixtures/*.json — fully
# offline, no keys needed. This is the default so `python main.py` just works.
DEMO_MODE = os.environ.get("DEMO_MODE", "true").strip().lower() in ("1", "true", "yes")

# Per-source raw-response cache TTL (seconds). Upstreams are never hit more
# than once per TTL regardless of request volume.
SOURCE_CACHE_TTL_S = int(os.environ.get("SOURCE_CACHE_TTL_S", "120"))
GEOCODE_CACHE_TTL_S = int(os.environ.get("GEOCODE_CACHE_TTL_S", "86400"))

# Routine departure window for alert matching: minutes before/after depart time.
DEPART_WINDOW_BEFORE_MIN = int(os.environ.get("DEPART_WINDOW_BEFORE_MIN", "30"))
DEPART_WINDOW_AFTER_MIN = int(os.environ.get("DEPART_WINDOW_AFTER_MIN", "90"))

# Corridor half-width for "is this event on my route" matching (v1: sampled
# straight line between origin and destination — see alerts/matcher.py).
CORRIDOR_RADIUS_M = int(os.environ.get("CORRIDOR_RADIUS_M", "800"))

# Upstream API keys — only required when DEMO_MODE=false.
TFNSW_API_KEY = os.environ.get("TFNSW_API_KEY", "")

# ---------------------------------------------------------------------------
# Ask-AI engine (services/ai.py) — server-side only, never sent to the client
# ---------------------------------------------------------------------------

# Optional Hugging Face token: enables the hosted Qwen chat model. Without it
# the service tries the local transformers Qwen, then falls back to a clearly
# labelled rule-based summary of the live data.
HF_TOKEN = os.environ.get("HF_TOKEN", "")
HF_CHAT_MODEL = os.environ.get("HF_CHAT_MODEL", "Qwen/Qwen2.5-7B-Instruct-1M:fastest")

REQUIRED_LIVE_KEYS = {
    "TFNSW_API_KEY": "Transport for NSW Open Data (https://opendata.transport.nsw.gov.au)",
}


def assert_live_keys_present() -> None:
    """Fail loudly at boot if DEMO_MODE is off and a required key is missing."""
    if DEMO_MODE:
        return
    missing = [name for name in REQUIRED_LIVE_KEYS if not os.environ.get(name)]
    if missing:
        lines = "\n".join(
            f"  {name}  — get one at: {REQUIRED_LIVE_KEYS[name]}" for name in missing
        )
        raise RuntimeError(
            "DEMO_MODE is false but required API keys are missing:\n"
            f"{lines}\n"
            "Set them in backend/.env (see .env.example), or run with DEMO_MODE=true."
        )

# ---------------------------------------------------------------------------
# Pipeline tunables
# ---------------------------------------------------------------------------

# Events further than this from a saved location are ignored for that location.
RELEVANCE_RADIUS_M = int(os.environ.get("RELEVANCE_RADIUS_M", "1000"))

# Optional proactive monitoring loop. Off by default so the demo flow
# (/demo/reset -> /monitor) stays deterministic. Set to "1" to show the
# "an alert you didn't ask for" feature (pitch Section 17).
ENABLE_BACKGROUND_MONITOR = os.environ.get("ENABLE_BACKGROUND_MONITOR", "0") == "1"
BACKGROUND_MONITOR_INTERVAL_S = int(os.environ.get("BACKGROUND_MONITOR_INTERVAL_S", "1800"))

# Comma-separated CORS origins ("*" = allow all — fine for a hackathon demo).
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",")]

# ---------------------------------------------------------------------------
# Optional local LLM refinement (pipeline/llm.py)
# ---------------------------------------------------------------------------

# "1" routes the deterministic explanation + recommendation through a small
# local Qwen model for warmer wording. Off by default: the deterministic path
# is instant and needs no extra packages. Enabling it requires
# `pip install transformers torch` and a one-time model download.
# Local Qwen is the reliable no-token fallback and is on by default. The model
# is downloaded from Hugging Face once and then reused from its local cache.
USE_LLM = os.environ.get("USE_LLM", "1") == "1"

# Any HF causal-LM id. Defaults to the smallest sensible Qwen instruct model so
# it runs on modest CPUs. Bump to Qwen/Qwen2.5-1.5B-Instruct (or Qwen/Qwen3-1.7B)
# for better wording if the machine has the RAM.
LLM_MODEL_ID = os.environ.get("LLM_MODEL_ID", "Qwen/Qwen2.5-0.5B-Instruct")

LLM_MAX_NEW_TOKENS = int(os.environ.get("LLM_MAX_NEW_TOKENS", "200"))

# "1" loads the model at startup instead of on the first request.
LLM_WARMUP = os.environ.get("LLM_WARMUP", "0") == "1"
