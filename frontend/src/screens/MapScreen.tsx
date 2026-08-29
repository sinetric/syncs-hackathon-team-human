import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { MapFeatures } from "../api/types";
import FeatureMap, { KIND_META } from "../components/FeatureMap";
import { ErrorNote, Skeleton, relativeTime, useFetch } from "../components/common";

const FILTERS = [
  "transport_disruption",
  "incident",
  "roadwork",
  "construction",
  "weather",
  "venue",
  "parking",
] as const;

const RADII = [500, 1000, 2000, 5000];
const SYDNEY_CBD: [number, number] = [-33.8688, 151.2093];
const REFRESH_MS = 60_000;

export default function MapScreen() {
  const places = useFetch(() => api.listPlaces());
  const [center, setCenter] = useState<[number, number] | null>(null);
  const [centerLabel, setCenterLabel] = useState("Sydney CBD");
  const [radiusM, setRadiusM] = useState(1000);
  const [enabled, setEnabled] = useState<Set<string>>(new Set(FILTERS));
  const [result, setResult] = useState<MapFeatures | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0); // bumps relative "last updated" text

  // centre priority: browser location -> saved Home -> first place -> CBD
  useEffect(() => {
    if (center) return;
    const data = places.data;
    const fallback = () => {
      if (data && data.length > 0) {
        const home = data.find((p) => /home/i.test(p.label)) ?? data[0];
        setCenter([home.lat, home.lng]);
        setCenterLabel(home.label);
      } else if (places.loading === false) {
        setCenter(SYDNEY_CBD);
        setCenterLabel("Sydney CBD");
      }
    };
    if (!navigator.geolocation) return fallback();
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setCenter([pos.coords.latitude, pos.coords.longitude]);
        setCenterLabel("your location");
      },
      fallback,
      { timeout: 4000, maximumAge: 300_000 },
    );
  }, [places.data, places.loading, center]);

  const load = useCallback(async (c: [number, number], r: number) => {
    setLoading(true);
    setError(null);
    try {
      setResult(await api.mapFeatures({ lat: c[0], lng: c[1], radius_m: r }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't load map data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!center) return;
    load(center, radiusM);
    const interval = setInterval(() => load(center, radiusM), REFRESH_MS);
    const ticker = setInterval(() => setTick((t) => t + 1), 15_000);
    return () => {
      clearInterval(interval);
      clearInterval(ticker);
    };
  }, [center, radiusM, load]);

  const visible = useMemo(
    () => (result?.data ?? []).filter((f) => enabled.has(f.kind) || !FILTERS.includes(f.kind as never)),
    [result, enabled],
  );

  if (!center) return <Skeleton lines={3} />;

  void tick; // read so the interval re-render refreshes relative timestamps

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between px-1">
        <p className="text-sm text-ink-soft">
          Around <span className="font-medium text-ink">{centerLabel}</span>
        </p>
        <select
          value={radiusM}
          onChange={(e) => setRadiusM(Number(e.target.value))}
          className="min-h-9 rounded-lg border border-line bg-card px-2 text-sm"
          aria-label="Search radius"
        >
          {RADII.map((r) => (
            <option key={r} value={r}>{r < 1000 ? `${r} m` : `${r / 1000} km`}</option>
          ))}
        </select>
      </div>

      {error ? (
        <ErrorNote message={error} onRetry={() => load(center, radiusM)} />
      ) : (
        <FeatureMap center={center} zoom={radiusM > 2000 ? 13 : radiusM > 900 ? 14 : 16} features={visible} radiusM={radiusM} heightClass="h-96" />
      )}

      <div className="rounded-2xl border border-line bg-card p-3">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-soft">Show on map</p>
        <div className="flex flex-wrap gap-1.5">
          {FILTERS.map((kind) => {
            const on = enabled.has(kind);
            return (
              <button
                key={kind}
                aria-pressed={on}
                onClick={() =>
                  setEnabled((prev) => {
                    const next = new Set(prev);
                    if (next.has(kind)) next.delete(kind);
                    else next.add(kind);
                    return next;
                  })
                }
                className={`min-h-9 rounded-full border px-2.5 py-1 text-xs font-medium ${
                  on ? "border-pine bg-pine-soft text-pine" : "border-line text-ink-soft opacity-60"
                }`}
              >
                {KIND_META[kind].emoji} {KIND_META[kind].label}
              </button>
            );
          })}
        </div>
        <p className="mt-2 text-xs text-ink-soft">
          {loading
            ? "Updating…"
            : result
              ? `${visible.length} of ${result.data.length} features · updated ${relativeTime(result.fetched_at)}`
              : ""}
          {result && !result.overpass_available && (
            <span className="block text-watch">
              OpenStreetMap (Overpass) is unreachable right now — showing alert data only.
            </span>
          )}
        </p>
      </div>
    </div>
  );
}
