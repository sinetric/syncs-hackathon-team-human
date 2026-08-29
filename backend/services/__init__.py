"""
External-data services (map, weather, parking, AI).

Each service is modular, cached, and degrades gracefully: a dead upstream
returns an empty/None result plus an availability flag — never a 500.
Route handlers and the AI context builder compose these; no API logic lives
in frontend components.
"""
