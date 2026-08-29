"""
Adapter interface.

Every source adapter subclasses SourceAdapter and implements `fetch_live`.
The base class handles the three cross-cutting rules:

  1. DEMO_MODE serves fixtures/<name>.json — fully offline, no keys.
  2. A dead source degrades to an empty list, never a 500.
  3. Raw fetches are cached per source (alerts/cache.py) so an upstream is
     never hit once per request per user.

Fixture format: a JSON list of SourceEvent-shaped objects. Times may be
absolute ISO strings, or relative to "now" via `valid_from_offset_mins` /
`valid_to_offset_mins` so the demo works on any day at any hour.
"""

from __future__ import annotations

import json
import logging
from datetime import timedelta

from config import DEMO_MODE, FIXTURES_DIR
from alerts.cache import cached
from alerts.events import SourceEvent
from timeutil import now_syd, parse_iso_syd

log = logging.getLogger("knowahead.adapters")


class SourceAdapter:
    name: str = "base"                # fixture filename stem + cache key
    display_name: str = "Unknown source"
    url: str | None = None

    def fetch_live(self) -> list[SourceEvent]:
        """Hit the real upstream and return normalised events. May raise —
        the base class catches everything."""
        raise NotImplementedError

    def events(self) -> list[SourceEvent]:
        try:
            if DEMO_MODE:
                return self._from_fixture()
            return cached(self.name, self.fetch_live)
        except Exception:
            log.exception("source %s failed; degrading to empty", self.name)
            return []

    # ------------------------------------------------------------------

    def _from_fixture(self) -> list[SourceEvent]:
        path = FIXTURES_DIR / f"{self.name}.json"
        if not path.exists():
            return []
        now = now_syd()
        events: list[SourceEvent] = []
        for item in json.loads(path.read_text(encoding="utf-8")):
            item = dict(item)
            if "valid_from_offset_mins" in item:
                item["valid_from"] = now + timedelta(minutes=item.pop("valid_from_offset_mins"))
            else:
                item["valid_from"] = parse_iso_syd(item["valid_from"])
            if "valid_to_offset_mins" in item:
                item["valid_to"] = now + timedelta(minutes=item.pop("valid_to_offset_mins"))
            else:
                item["valid_to"] = parse_iso_syd(item["valid_to"])
            item.setdefault("source_name", self.display_name)
            item.setdefault("source_url", self.url)
            item["fetched_at"] = now
            events.append(SourceEvent(**item))
        return events
