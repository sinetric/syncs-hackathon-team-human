"""
Optional local LLM refinement of the deterministic summary.

Enabled with USE_LLM=1. The model NEVER sees raw data sources and never decides
facts: it receives the already-verified structured signals plus the
deterministic draft from pipeline/summary.py, and only rewrites them into a
warmer, more personal wording.

Any failure — model not installed, weights missing, malformed output, exception —
falls straight back to the deterministic text. The endpoint can't break because
the LLM is unhappy.

Runs on CPU via Hugging Face transformers. Default model is a tiny Qwen instruct
model so it works on modest machines; override with LLM_MODEL_ID.
"""

from __future__ import annotations

import json
import re
import threading

from config import LLM_MAX_NEW_TOKENS, LLM_MODEL_ID
from models import DetectedChange, SavedLocation

_lock = threading.Lock()
_model = None
_tokenizer = None


def _load():
    """Lazy, thread-safe singleton load of the model + tokenizer."""
    global _model, _tokenizer
    if _model is not None:
        return _model, _tokenizer
    with _lock:
        if _model is None:
            from transformers import AutoModelForCausalLM, AutoTokenizer

            tok = AutoTokenizer.from_pretrained(LLM_MODEL_ID)
            mdl = AutoModelForCausalLM.from_pretrained(LLM_MODEL_ID)
            mdl.eval()
            _tokenizer, _model = tok, mdl
    return _model, _tokenizer


def warmup() -> None:
    """Load weights now so the first real request isn't slow."""
    _load()


_SYSTEM = (
    "You are the explanation layer of Know Ahead, a personal urban-intelligence "
    "app for Sydney. You receive VERIFIED facts about a change near a place the "
    "user cares about, plus a plain draft. Rewrite the draft into two short, warm, "
    "plain-English fields.\n"
    "Rules: use ONLY the given facts; invent nothing; introduce no new numbers, "
    "dates or place names; keep impact as *potential* impact, never certainty; the "
    "recommendation must be an action to investigate or prepare, not a decision "
    "made for the user.\n"
    'Reply with ONLY a JSON object: {"explanation": "...", "recommendation": "..."}'
)


def refine(
    location: SavedLocation,
    detected: list[DetectedChange],
    draft_explanation: str,
    draft_recommendation: str,
    question: str | None = None,
) -> tuple[str, str]:
    """Return (explanation, recommendation). Falls back to the drafts on any error."""
    payload = {
        "location_label": location.label,
        "works_from_home": location.works_from_home,
        "lease_end_date": str(location.lease_end_date) if location.lease_end_date else None,
        "user_question": question,
        "changes": [
            {
                "type": c.event.type.value,
                "title": c.event.title,
                "change_type": c.change_type.value,
                "distance_m": round(c.distance_m),
                "duration_days": c.impact.duration_days,
                "potential_impact": {
                    "noise": c.impact.noise.value,
                    "traffic": c.impact.traffic.value,
                    "dust": c.impact.dust.value,
                },
            }
            for c in detected
        ],
        "draft_explanation": draft_explanation,
        "draft_recommendation": draft_recommendation,
    }
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]

    try:
        model, tok = _load()

        try:
            prompt = tok.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,  # Qwen3: skip <think> block; Qwen2.5 ignores it
            )
        except TypeError:
            prompt = tok.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

        import torch

        inputs = tok(prompt, return_tensors="pt")
        with torch.no_grad():
            generated = model.generate(
                **inputs,
                max_new_tokens=LLM_MAX_NEW_TOKENS,
                do_sample=False,  # greedy -> stable demo output
                pad_token_id=tok.eos_token_id,
            )
        text = tok.decode(
            generated[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True
        )
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)

        data = json.loads(_first_json_object(text))
        explanation = str(data["explanation"]).strip()
        recommendation = str(data["recommendation"]).strip()
        if explanation and recommendation:
            print(f"[llm] refined via {LLM_MODEL_ID}")
            return explanation, recommendation
        raise ValueError("model returned empty fields")

    except Exception as exc:  # noqa: BLE001 - any failure -> deterministic fallback
        print(f"[llm] using deterministic summary ({exc!r})")
        return draft_explanation, draft_recommendation


def _first_json_object(text: str) -> str:
    """Extract the first balanced {...} block from possibly-chatty model output."""
    start = text.find("{")
    if start == -1:
        raise ValueError("no JSON object in model output")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise ValueError("no complete JSON object in model output")
