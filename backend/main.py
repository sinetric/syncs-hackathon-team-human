"""
Know Ahead — Backend MVP
=========================
Pipeline (pitch doc, Section 9):

    Data sources -> Normalisation -> Geospatial filtering -> Change detection
        -> Impact scoring -> Explanation + recommendation -> Alert

Design rule the whole backend follows (Section 22):
    Code establishes the facts.
Distance (geo.py), change detection (pipeline/changes.py), impact scoring
(pipeline/impact.py) and the explanation + recommendation (pipeline/summary.py)
are all deterministic Python — no model calls. A natural-language
interpretation layer can be slotted in behind pipeline/summary.py later without
touching anything else.

Module map:
    config.py            paths + tunables
    geo.py               haversine / radius helpers (geospatial maths live here)
    models.py            pydantic schemas (single source of truth)
    store.py             flat-file persistence
    sources/             data-source adapters (planning seed today; add more)
    pipeline/            change detection, impact scoring, summary, orchestration
    routes/              FastAPI routers

Run:  python main.py            (or:  uvicorn main:app --reload)
"""

from __future__ import annotations

import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from config import (
    BACKGROUND_MONITOR_INTERVAL_S,
    CORS_ORIGINS,
    ENABLE_BACKGROUND_MONITOR,
    LLM_MODEL_ID,
    LLM_WARMUP,
    USE_LLM,
    assert_live_keys_present,
)
from pipeline.run import run_pipeline_for_location
from routes import api_v1, locations, monitor
from store import load_locations, save_pulse

assert_live_keys_present()


async def _monitor_loop() -> None:
    """Proactive monitoring (pitch Section 17): periodically re-run the pipeline
    for every saved location and cache the result for GET /pulse/{id}."""
    while True:
        for location in load_locations():
            with contextlib.suppress(Exception):
                result = run_pipeline_for_location(location)
                save_pulse(location.id, result.model_dump(mode="json"))
        await asyncio.sleep(BACKGROUND_MONITOR_INTERVAL_S)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if USE_LLM and LLM_WARMUP:
        from pipeline import llm

        llm.warmup()

    task = asyncio.create_task(_monitor_loop()) if ENABLE_BACKGROUND_MONITOR else None
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


app = FastAPI(title="Know Ahead API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(locations.router)
app.include_router(monitor.router)
app.include_router(api_v1.router)


# Contract error envelope: { "error": { "code": "...", "message": "..." } }
@app.exception_handler(HTTPException)
async def http_exception_envelope(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        error = exc.detail
    else:
        error = {"code": "http_error", "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content={"error": error})


@app.exception_handler(RequestValidationError)
async def validation_exception_envelope(request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    where = ".".join(str(part) for part in first.get("loc", []))
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": f"{where}: {first.get('msg', 'invalid request')}",
            }
        },
    )


@app.get("/health", tags=["meta"])
def health():
    return {
        "status": "ok",
        "llm": {"enabled": USE_LLM, "model": LLM_MODEL_ID if USE_LLM else None},
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
