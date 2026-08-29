"""
Ask-AI service: Qwen wired to the application's live data.

    Frontend -> POST /api/v1/ask -> build_context() -> engine -> answer

The model never invents facts: it receives a JSON context assembled from the
alert engine, live weather, journey preview, and parking estimates, and is
instructed to answer only from it. Engines, in order of preference:

  huggingface_api  Qwen chat via the HF router (HF_TOKEN, server-side only)
  local_qwen       the repo's transformers Qwen (pipeline/llm.py singleton)
  rules            deterministic composition of the same context, explicitly
                   labelled "AI model unavailable" — never passed off as Qwen

Every response says which engine produced it.
"""

from __future__ import annotations

import json
import logging

import requests

from config import HF_CHAT_MODEL, HF_TOKEN, LLM_MODEL_ID
from alerts import build_alerts
from journeys import build_preview
from models import Severity, TravelMode
from pipeline.llm import _first_json_object
from services.parking import find_parking
from services.weather import get_weather
from store import get_place, load_places, load_routines
from timeutil import now_syd

log = logging.getLogger("knowahead.ai")

_SYSTEM = (
    "You are Know Ahead's assistant for Sydney. You receive a JSON snapshot of "
    "the user's live app data: saved places, routines, current alerts (severity "
    "act > watch > info), observed weather with derived signals, an optional "
    "journey preview, and estimated parking probabilities.\n"
    "Rules: answer ONLY from the snapshot; never invent events, numbers, or "
    "places; distinguish observed data from estimates (parking probabilities "
    "and delay minutes are estimates); keep answers short, second person, "
    "plain verbs; recommend concrete actions when alerts justify them.\n"
    'Reply with ONLY a JSON object: {"answer": "2-4 sentences", '
    '"factors": ["short bullet per underlying fact used"], '
    '"confidence_pct": <int 0-100 or null>}'
)


# ---------------------------------------------------------------------------
# Context builder — everything the model may know, all from live services
# ---------------------------------------------------------------------------


def build_context(
    origin_id: str | None = None,
    dest_id: str | None = None,
    question: str = "",
) -> dict:
    now = now_syd()
    places = load_places()
    routines = load_routines()
    alerts = build_alerts(window_mins=360)

    context: dict = {
        "now": now.isoformat(),
        "places": [p.model_dump() for p in places],
        "routines": [r.model_dump(mode="json") for r in routines],
        "alerts": [
            {
                "kind": a.kind.value,
                "severity": a.severity.value,
                "title": a.title,
                "body": a.body,
                "delay_minutes_estimate": a.impact.delay_minutes,
                "confidence": a.impact.confidence,
                "source": a.source.name,
            }
            for a in alerts[:12]
        ],
    }

    anchor = get_place(origin_id) if origin_id else (places[0] if places else None)
    if anchor is not None:
        weather, available = get_weather(anchor.lat, anchor.lng)
        context["weather"] = weather if available else {"unavailable": True}
        context["weather_location"] = anchor.label

    origin = get_place(origin_id) if origin_id else None
    dest = get_place(dest_id) if dest_id else None
    if origin and dest:
        preview = build_preview(origin, dest, now_syd(), TravelMode.transit)
        context["journey"] = {
            "from": origin.label,
            "to": dest.label,
            "duration_minutes": preview.duration_minutes,
            "trip_mode": preview.trip_mode.value,
            "legs": [f"{leg.mode.value} {leg.from_} to {leg.to}" for leg in preview.legs],
            "checklist": [c.label for c in preview.checklist],
        }
    target = dest or anchor
    wants_parking = any(word in question.casefold() for word in ("park", "parking", "car space"))
    if target is not None and wants_parking:
        raining = bool(
            (context.get("weather") or {}).get("derived", {}).get("raining_now")
        )
        event_count = sum(1 for a in alerts if a.severity != Severity.info)
        spots, available = find_parking(
            target.lat,
            target.lng,
            1200,
            now,
            event_count,
            raining,
            timeout_s=3,
            max_mirrors=1,
        )
        context["parking_near"] = target.label
        context["parking"] = (
            [
                {
                    "name": s["name"],
                    "distance_m": s["distance_m"],
                    "estimated_probability_pct": s["probability"]["value_pct"],
                    "reasons": s["probability"]["reasons"][:3],
                }
                for s in spots[:5]
            ]
            if available
            else {"unavailable": True}
        )
    return context


# ---------------------------------------------------------------------------
# Engines
# ---------------------------------------------------------------------------


def ask(question: str, origin_id: str | None = None, dest_id: str | None = None) -> dict:
    context = build_context(origin_id, dest_id, question)
    messages = [
        {"role": "system", "content": _SYSTEM},
        {
            "role": "user",
            "content": f"App data snapshot:\n{json.dumps(context, ensure_ascii=False)}\n\nQuestion: {question}",
        },
    ]

    for engine, runner in (("huggingface_api", _ask_hf), ("local_qwen", _ask_local)):
        try:
            parsed = runner(messages)
            if parsed is not None:
                return _shape(parsed, engine, context)
        except Exception as exc:  # noqa: BLE001 — degrade to the next engine
            log.warning("engine %s failed: %r", engine, exc)

    return _shape(_ask_rules(question, context), "rules", context)


def _shape(parsed: dict, engine: str, context: dict) -> dict:
    model = {
        "huggingface_api": HF_CHAT_MODEL,
        "local_qwen": f"{LLM_MODEL_ID} (local Hugging Face model)",
        "rules": None,
    }[engine]
    return {
        "answer": str(parsed.get("answer", "")).strip(),
        "factors": [str(f) for f in parsed.get("factors", [])][:8],
        "confidence_pct": parsed.get("confidence_pct"),
        "engine": engine,
        "model": model,
        "disclaimer": (
            "Rule-based summary of live app data — the Qwen model is not "
            "available on this server." if engine == "rules"
            else "AI-generated from live app data; delay and parking figures are estimates."
        ),
        "context_used": sorted(
            k for k in context if k in ("alerts", "weather", "journey", "parking", "routines", "places")
        ),
    }


def _ask_hf(messages: list[dict]) -> dict | None:
    if not HF_TOKEN:
        return None
    resp = requests.post(
        "https://router.huggingface.co/v1/chat/completions",
        headers={"Authorization": f"Bearer {HF_TOKEN}"},
        json={
            "model": HF_CHAT_MODEL,
            "messages": messages,
            "max_tokens": 400,
            "temperature": 0.2,
            "stream": False,
        },
        timeout=(8, 45),
    )
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"]
    parsed = json.loads(_first_json_object(text))
    if not str(parsed.get("answer", "")).strip():
        raise ValueError("Qwen returned an empty answer")
    return parsed


def _ask_local(messages: list[dict]) -> dict | None:
    # Same opt-in flag the legacy pipeline uses: local CPU inference takes
    # minutes per question, so it must be a deliberate choice, and the rules
    # engine below is honest about the model being off.
    from config import USE_LLM

    if not USE_LLM:
        return None
    try:
        from pipeline.llm import _load
        import torch  # noqa: F401
    except ImportError:
        return None
    model, tok = _load()
    try:
        prompt = tok.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
        )
    except TypeError:
        prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    import torch

    inputs = tok(prompt, return_tensors="pt")
    with torch.no_grad():
        generated = model.generate(
            **inputs, max_new_tokens=300, do_sample=False, pad_token_id=tok.eos_token_id
        )
    text = tok.decode(generated[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    import re

    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    try:
        return json.loads(_first_json_object(text))
    except (ValueError, json.JSONDecodeError):
        # small local models sometimes answer in prose instead of JSON —
        # that's still a real Qwen answer, so keep it rather than discard it
        if len(text) < 20:
            raise
        return {"answer": text[:700], "factors": [], "confidence_pct": None}


def _ask_rules(question: str, context: dict) -> dict:
    """Deterministic composition of the same live context. Not a chatbot and
    not pretending to be one — the response is labelled rule-based."""
    factors: list[str] = []
    parts: list[str] = []

    acts = [a for a in context.get("alerts", []) if a["severity"] == "act"]
    watches = [a for a in context.get("alerts", []) if a["severity"] == "watch"]
    if acts:
        lead = acts[0]
        delay = lead.get("delay_minutes_estimate")
        parts.append(
            f"The biggest thing right now: {lead['title']}."
            + (f" Allow about {delay} extra minutes (estimate)." if delay else "")
        )
        factors.extend(f"{a['title']} ({a['source']})" for a in acts[:3])
    elif watches:
        parts.append(f"Nothing urgent, but worth watching: {watches[0]['title']}.")
        factors.extend(f"{a['title']} ({a['source']})" for a in watches[:3])
    else:
        parts.append("No active alerts on your saved places or routines right now.")

    weather = context.get("weather") or {}
    signals = weather.get("derived", {}).get("signals", [])
    if signals:
        parts.append(signals[0])
        factors.extend(signals[:2])
    elif weather.get("observed"):
        obs = weather["observed"]
        factors.append(
            f"Weather at {context.get('weather_location', 'your area')}: "
            f"{obs.get('conditions')}, {obs.get('temperature_c')}°C (observed)"
        )

    journey = context.get("journey")
    if journey:
        parts.append(
            f"Your {journey['from']} to {journey['to']} trip is about "
            f"{journey['duration_minutes']} min door to door right now."
        )
        factors.append(f"Journey preview: {journey['duration_minutes']} min, {journey['trip_mode']} trip")

    parking = context.get("parking")
    if isinstance(parking, list) and parking and "park" in question.lower():
        best = max(parking, key=lambda p: p["estimated_probability_pct"])
        parts.append(
            f"Best parking bet near {context.get('parking_near')}: {best['name']} "
            f"({best['distance_m']} m away, ~{best['estimated_probability_pct']}% estimated chance)."
        )
        factors.append("Parking probabilities are heuristic estimates, not live occupancy")

    return {"answer": " ".join(parts), "factors": factors, "confidence_pct": None}
