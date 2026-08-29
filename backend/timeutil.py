"""
Timezone helpers. Every timestamp in the v1 API is timezone-aware
Australia/Sydney — no naive datetimes anywhere (contract rule).
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from config import APP_TZ

SYDNEY = ZoneInfo(APP_TZ)

_WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def now_syd() -> datetime:
    return datetime.now(SYDNEY)


def to_syd(dt: datetime) -> datetime:
    """Coerce any datetime to aware Sydney time. Naive input is assumed Sydney."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=SYDNEY)
    return dt.astimezone(SYDNEY)


def parse_iso_syd(value: str) -> datetime:
    return to_syd(datetime.fromisoformat(value))


def weekday_code(dt: datetime) -> str:
    return _WEEKDAYS[dt.weekday()]


def next_departure(days: list[str], depart_local_time: str, ref: datetime | None = None) -> datetime | None:
    """Next occurrence (>= ref) of a routine's local departure time on one of
    its weekdays, in Sydney time. None if `days` is empty."""
    if not days:
        return None
    ref = ref or now_syd()
    hh, mm = (int(part) for part in depart_local_time.split(":"))
    for offset in range(8):
        day = ref + timedelta(days=offset)
        candidate = datetime.combine(day.date(), time(hh, mm), tzinfo=SYDNEY)
        if weekday_code(candidate) in days and candidate >= ref:
            return candidate
    return None
