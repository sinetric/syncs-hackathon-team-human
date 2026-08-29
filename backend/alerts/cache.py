"""
Per-source TTL cache for raw upstream responses.

Rule (docs/api-contract.md build notes): never call an upstream API once per
request per user. Every adapter fetch goes through `cached`.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from config import SOURCE_CACHE_TTL_S

_cache: dict[str, tuple[float, Any]] = {}


def cached(key: str, fetch: Callable[[], Any], ttl_s: int = SOURCE_CACHE_TTL_S) -> Any:
    """Return the cached value for `key` if fresh, else call `fetch` and store it."""
    now = time.monotonic()
    hit = _cache.get(key)
    if hit is not None and now - hit[0] < ttl_s:
        return hit[1]
    value = fetch()
    _cache[key] = (now, value)
    return value


def clear() -> None:
    _cache.clear()
