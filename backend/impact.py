"""
impact.py — deterministic impact scoring + AI reliability guardrail.

Design contract:  AI is primary, this file is the safety net.
  - score_all()  computes a rule-based impact score for every event.
                 It runs on EVERY request, but the user normally never
                 sees it, the AI answer is what's shown.
  - find_issues()/trustworthy()  compare the AI's answer against the verified facts
                 (and against the scores) to catch hallucination, invented events or
                 altered distances.
  - fallback()   turns the deterministic scores into an /analyze formatted response, so a
                 failed or untrustworthy AI call still renders a real impact card
                 instead of a blank one.

Dependency-free (stdlib only). Operates on plain UrbanEvent dicts that already have
`distance_m` set by geo.py.

    from app import impact

    scored = impact.score_all(events, user_ctx)      # always
    try:
        ai = call_claude(events, user_ctx)
        if impact.find_issues(ai, events):           # AI answered but failed the guardrail
            result = impact.fallback(scored)
        else:
            result = ai                              # happy path
    except (Timeout, JSONDecodeError, APIError):
        result = impact.fallback(scored)             # AI unavailable
"""

from datetime import date

# ── Scoring model ──────────────────────────────────────────────────────────────

# Base weight of each impact factor produced by an event type (0–1).
TYPE_PROFILE = {
    "development": {"noise": 0.8, "dust": 0.6, "traffic": 0.5, "access": 0.3},
    "roadwork":    {"traffic": 0.7, "access": 0.6, "noise": 0.3},
    "incident":    {"traffic": 0.7, "safety": 0.5, "access": 0.4},
    "flood":       {"access": 0.8, "safety": 0.7, "traffic": 0.5},
    "event":       {"traffic": 0.6, "noise": 0.5, "access": 0.5},
    "weather":     {"safety": 0.4, "access": 0.3},
}

# How the user's situation reweights factors. Missing factor → neutral (1.0).
EXPOSURE = {
    "wfh":      {"noise": 1.3, "dust": 1.1},
    "commuter": {"noise": 0.7, "traffic": 1.3, "access": 1.2},
}

TYPE_LABEL = {
    "development": "Development / construction", "roadwork": "Roadwork",
    "incident": "Traffic incident", "flood": "Flooding",
    "event": "Major event", "weather": "Weather",
}

DEFAULT_RECOMMENDATION = {
    "development": "Check permitted construction hours and expected duration before making commitments.",
    "roadwork": "Allow extra travel time and check for alternative routes.",
    "incident": "Expect delays in the area; check live traffic before setting out.",
    "flood": "Avoid low-lying routes and monitor conditions before travelling.",
    "event": "Expect crowds, parking pressure, and added noise around the area.",
    "weather": "Plan outdoor activity around the forecast.",
}

LONG_DURATION_FACTORS = ("noise", "dust")   # ongoing works keep producing these
LONG_DURATION_MONTHS = 3


def proximity_mult(distance_m):
    """Closer events hit harder. Stepwise."""
    if distance_m <= 100:  return 1.0
    if distance_m <= 250:  return 0.8
    if distance_m <= 500:  return 0.6
    if distance_m <= 1000: return 0.4
    return 0.2


def _duration_months(event):
    """Whole months between start_date and end_date, or 0 if unparseable."""
    try:
        s = date.fromisoformat(event["start_date"])
        e = date.fromisoformat(event["end_date"])
    except (KeyError, TypeError, ValueError):
        return 0
    return max(0, (e.year - s.year) * 12 + (e.month - s.month))


def band(score):
    if score >= 0.66: return "high"
    if score >= 0.33: return "medium"
    if score > 0:     return "low"
    return "none"


def score_event(event, user_ctx):
    """Return {factor: {'score': float, 'rating': str}} for one event."""
    profile = TYPE_PROFILE.get(event.get("type"), {})
    prox = proximity_mult(event.get("distance_m", 99_999))
    long_job = _duration_months(event) >= LONG_DURATION_MONTHS
    exposure = EXPOSURE.get((user_ctx or {}).get("exposure"), {})

    out = {}
    for factor, base in profile.items():
        score = base * prox
        if long_job and factor in LONG_DURATION_FACTORS:
            score *= 1.2
        score *= exposure.get(factor, 1.0)
        score = min(score, 1.0)                       # cap
        out[factor] = {"score": round(score, 3), "rating": band(score)}
    return out


def score_all(events, user_ctx):
    """Deterministic scores for every event, keyed by event id."""
    return {
        e.get("id"): {
            "type": e.get("type"),
            "distance_m": e.get("distance_m"),
            "factors": score_event(e, user_ctx),
        }
        for e in events
    }


# ── Reliability guardrail ───────────────────────────────────────────────────────

def find_issues(ai_response, events, scored=None, distance_tolerance_m=25):
    """Return a list of problems with the AI response. Empty list = trustworthy.

    Cheap, high-value checks that catch the scariest failure — fabricated facts:
      1. Every event_id the AI references must exist in the verified input.
      2. Any distance the AI reports must match geo.py's (it's given, not derived).
    Optional third check (only if `scored` passed): flag a wild rating divergence,
    e.g. the formula says High but the AI says None for the same factor.
    """
    issues = []
    valid_ids = {e.get("id") for e in events}
    by_id = {e.get("id"): e for e in events}

    for ae in ai_response.get("events", []):
        eid = ae.get("event_id")

        if eid not in valid_ids:
            issues.append(f"AI referenced unknown event_id '{eid}' (not in verified data)")
            continue

        ai_dist = ae.get("distance_m")
        true_dist = by_id[eid].get("distance_m")
        if ai_dist is not None and true_dist is not None:
            if abs(ai_dist - true_dist) > distance_tolerance_m:
                issues.append(
                    f"AI distance {ai_dist}m for '{eid}' contradicts verified {true_dist}m")

        if scored and eid in scored:
            det = scored[eid]["factors"]
            for imp in ae.get("impacts", []):
                f, r = imp.get("factor"), imp.get("rating")
                if f in det and _rank(det[f]["rating"]) - _rank(r) >= 2:
                    issues.append(
                        f"AI rated {f} '{r}' for '{eid}' but formula says '{det[f]['rating']}'")
    return issues


def trustworthy(ai_response, events, scored=None):
    """Boolean convenience wrapper: True if the AI response passes all checks."""
    return not find_issues(ai_response, events, scored)


_RATING_ORDER = ["none", "low", "medium", "high"]
def _rank(r):
    return _RATING_ORDER.index(r) if r in _RATING_ORDER else 0


# ── Fallback response ───────────────────────────────────────────────────────────

def fallback(scored, top_n=5):
    """Build an /analyze-shaped response from deterministic scores only.

    Rendered when the AI is unavailable or untrustworthy. Honest about it:
    confidence is 'low' and language is templated, not invented.
    """
    events_out = []
    # Nearest first, so the hero (closest) event leads.
    for eid, s in sorted(scored.items(), key=lambda kv: kv[1]["distance_m"] or 99_999):
        etype = s["type"]
        dist = s["distance_m"]
        impacts = [
            {"factor": f, "rating": v["rating"], "basis": "inferred"}
            for f, v in s["factors"].items() if v["rating"] != "none"
        ]
        impacts.sort(key=lambda i: _rank(i["rating"]), reverse=True)
        top = impacts[0] if impacts else None

        events_out.append({
            "event_id": eid,
            "summary": f"{TYPE_LABEL.get(etype, 'Change')} detected {dist}m from your home.",
            "distance_m": dist,
            "impacts": impacts,
            "why_it_matters": (
                f"Likely {top['rating']} {top['factor']} impact given it's {dist}m away."
                if top else f"Detected {dist}m away; limited expected impact."),
            "recommendation": DEFAULT_RECOMMENDATION.get(
                etype, "Review this change and consider whether it affects your plans."),
            "confidence": "low",
            "evidence": [
                f"{TYPE_LABEL.get(etype, 'Event')} {dist}m away",
                "Impact estimated by deterministic scorer (AI interpretation unavailable)",
            ],
        })
        if len(events_out) >= top_n:
            break

    headline = (f"Change detected near your home — {events_out[0]['distance_m']}m away."
                if events_out else "No significant changes detected near your home.")
    return {"headline": headline, "events": events_out,
            "decision_answer": None, "degraded": True}
