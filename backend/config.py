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
USE_LLM = os.environ.get("USE_LLM", "0") == "1"

# Any HF causal-LM id. Defaults to the smallest sensible Qwen instruct model so
# it runs on modest CPUs. Bump to Qwen/Qwen2.5-1.5B-Instruct (or Qwen/Qwen3-1.7B)
# for better wording if the machine has the RAM.
LLM_MODEL_ID = os.environ.get("LLM_MODEL_ID", "Qwen/Qwen2.5-0.5B-Instruct")

LLM_MAX_NEW_TOKENS = int(os.environ.get("LLM_MAX_NEW_TOKENS", "200"))

# "1" loads the model at startup instead of on the first request.
LLM_WARMUP = os.environ.get("LLM_WARMUP", "0") == "1"
