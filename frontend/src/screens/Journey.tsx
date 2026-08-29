import { useEffect, useState } from "react";
import { Marker, Polyline, Popup } from "react-leaflet";
import { api } from "../api/client";
import type { JourneyPreview, LegMode, ParkingSpot, TravelMode, Weather } from "../api/types";
import AlertCard from "../components/AlertCard";
import FeatureMap, { labelIcon } from "../components/FeatureMap";
import { ErrorNote, Skeleton, localHm, useFetch } from "../components/common";

const LEG_LABEL: Record<LegMode, string> = {
  walk: "Walk",
  train: "Train",
  bus: "Bus",
  lightrail: "Light rail",
  ferry: "Ferry",
  drive: "Drive",
};

const FARE_BASIS: Record<string, string> = {
  opal_adult_peak: "Opal adult, peak",
  opal_adult_offpeak: "Opal adult, off-peak",
  fuel_estimate: "fuel, rough",
  free: "free",
};

export default function Journey() {
  const places = useFetch(() => api.listPlaces());
  const [originId, setOriginId] = useState("");
  const [destId, setDestId] = useState("");
  const [mode, setMode] = useState<TravelMode>("transit");
  const [departAt, setDepartAt] = useState(""); // datetime-local value; empty = now
  const [preview, setPreview] = useState<JourneyPreview | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [ticked, setTicked] = useState<Set<string>>(new Set());
  const [parking, setParking] = useState<ParkingSpot[] | null>(null);
  const [parkingNote, setParkingNote] = useState<string | null>(null);
  const [weather, setWeather] = useState<Weather | null>(null);

  useEffect(() => {
    const data = places.data;
    if (data && data.length >= 2 && !originId) {
      setOriginId(data[0].id);
      setDestId(data[1].id);
    }
  }, [places.data, originId]);

  const loadPreview = async () => {
    if (!originId || !destId || originId === destId) {
      setPreviewError("Pick two different places first.");
      return;
    }
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      const result = await api.journeyPreview({
        origin_id: originId,
        dest_id: destId,
        mode,
        depart_at: departAt ? new Date(departAt).toISOString() : undefined,
      });
      setPreview(result);
      setTicked(new Set());
      // enrich with live data around the destination — each degrades alone
      const dest = (places.data ?? []).find((p) => p.id === destId);
      if (dest) {
        api.parking({ lat: dest.lat, lng: dest.lng, radius_m: 800 })
          .then((r) => {
            setParking(r.data.slice(0, 4));
            setParkingNote(null);
          })
          .catch(() => {
            setParking(null);
            setParkingNote("Parking search unavailable right now (OpenStreetMap unreachable).");
          });
        api.weather(dest.lat, dest.lng)
          .then(setWeather)
          .catch(() => setWeather(null));
      }
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : "Couldn't load the preview.");
    } finally {
      setPreviewLoading(false);
    }
  };

  if (places.loading) return <Skeleton lines={3} />;
  if (places.error) return <ErrorNote message={places.error.message} onRetry={places.reload} />;

  const placeList = places.data ?? [];
  if (placeList.length < 2) {
    return (
      <div className="mt-16 text-center">
        <h2 className="display text-xl font-bold">Two places make a journey.</h2>
        <p className="mt-2 text-sm text-ink-soft">Save at least two places first, then preview the trip between them.</p>
      </div>
    );
  }

  const selectClass =
    "min-h-11 w-full rounded-xl border border-line bg-card px-3 py-2 text-sm";

  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-line bg-card p-4">
        <div className="grid grid-cols-2 gap-3">
          <label className="text-sm">
            <span className="mb-1 block font-medium">From</span>
            <select value={originId} onChange={(e) => setOriginId(e.target.value)} className={selectClass}>
              {placeList.map((p) => (
                <option key={p.id} value={p.id}>{p.label}</option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="mb-1 block font-medium">To</span>
            <select value={destId} onChange={(e) => setDestId(e.target.value)} className={selectClass}>
              {placeList.map((p) => (
                <option key={p.id} value={p.id}>{p.label}</option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="mb-1 block font-medium">Leaving</span>
            <input
              type="datetime-local"
              value={departAt}
              onChange={(e) => setDepartAt(e.target.value)}
              className={selectClass}
              aria-label="Departure time, leave empty for now"
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block font-medium">Mode</span>
            <select value={mode} onChange={(e) => setMode(e.target.value as TravelMode)} className={selectClass}>
              <option value="transit">Transit</option>
              <option value="drive">Drive</option>
              <option value="walk">Walk</option>
            </select>
          </label>
        </div>
        <button
          onClick={loadPreview}
          disabled={previewLoading}
          className="mt-4 min-h-11 w-full rounded-xl bg-pine font-medium text-white disabled:opacity-60"
        >
          {previewLoading ? "Checking the network…" : "Preview journey"}
        </button>
        {previewError && <p className="mt-2 text-sm text-act">{previewError}</p>}
      </section>

      {previewLoading && <Skeleton lines={3} />}

      {preview && !previewLoading && (() => {
        const origin = placeList.find((p) => p.id === originId);
        const dest = placeList.find((p) => p.id === destId);
        const mapFeatures = [
          ...preview.alerts
            .filter((a) => a.geo)
            .map((a) => ({
              id: a.id,
              kind: a.kind,
              name: a.title,
              lat: a.geo!.lat,
              lng: a.geo!.lng,
              tags: {},
              alert: a,
              source: a.source,
            })),
          ...(parking ?? []),
        ];
        return (
        <>
          {origin && dest && (
            <FeatureMap
              center={[(origin.lat + dest.lat) / 2, (origin.lng + dest.lng) / 2]}
              zoom={13}
              features={mapFeatures}
              heightClass="h-72"
            >
              <Marker position={[origin.lat, origin.lng]} icon={labelIcon("A", "origin")}>
                <Popup>{origin.label} — origin</Popup>
              </Marker>
              <Marker position={[dest.lat, dest.lng]} icon={labelIcon("B", "dest")}>
                <Popup>{dest.label} — destination</Popup>
              </Marker>
              {/* visual connection only — not a navigation route */}
              <Polyline
                positions={[[origin.lat, origin.lng], [dest.lat, dest.lng]]}
                pathOptions={{ color: "#1e5c48", weight: 2, dashArray: "6 8", opacity: 0.7 }}
              />
            </FeatureMap>
          )}

          <section className="rounded-2xl border border-line bg-card p-4">
            <div className="flex items-baseline justify-between">
              <p className="display text-3xl font-bold">
                {preview.duration_minutes} min
                <span className="ml-2 rounded-full bg-info-bg px-2 py-0.5 align-middle text-xs font-semibold text-info">
                  {preview.trip_mode === "long" ? "long trip" : "short trip"}
                </span>
              </p>
              <p className="text-sm text-ink-soft">
                ~${(preview.fare.estimate_cents / 100).toFixed(2)}
                <span className="block text-right text-xs">{FARE_BASIS[preview.fare.basis] ?? preview.fare.basis} est.</span>
              </p>
            </div>

            <ol className="mt-4 space-y-2">
              {preview.legs.map((leg) => (
                <li key={leg.index} className="flex items-center gap-3 rounded-xl bg-paper px-3 py-2.5">
                  <span className="w-16 shrink-0 rounded-lg bg-pine-soft px-2 py-1 text-center text-xs font-semibold text-pine">
                    {LEG_LABEL[leg.mode]}
                  </span>
                  <span className="min-w-0 flex-1 text-sm">
                    {leg.from} → {leg.to}
                    {leg.line && <span className="ml-1 text-xs text-ink-soft">({leg.line})</span>}
                  </span>
                  <span className="shrink-0 text-xs tabular-nums text-ink-soft">
                    {localHm(leg.depart_at)} · {leg.duration_minutes}m
                  </span>
                </li>
              ))}
            </ol>
          </section>

          {preview.checklist.length > 0 && (
            <section className="rounded-2xl border border-line bg-card p-4">
              <h3 className="display font-semibold">Before you leave</h3>
              <ul className="mt-2 space-y-1">
                {preview.checklist.map((item) => (
                  <li key={item.id}>
                    <label className="flex min-h-11 cursor-pointer items-center gap-3 rounded-xl px-2 py-1.5 hover:bg-paper">
                      <input
                        type="checkbox"
                        checked={ticked.has(item.id)}
                        onChange={() =>
                          setTicked((prev) => {
                            const next = new Set(prev);
                            if (next.has(item.id)) next.delete(item.id);
                            else next.add(item.id);
                            return next;
                          })
                        }
                        className="h-5 w-5 accent-(--color-pine)"
                      />
                      <span className={ticked.has(item.id) ? "text-ink-soft line-through" : ""}>
                        {item.label}
                        <span className="block text-xs text-ink-soft no-underline">{item.reason}</span>
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {weather && (
            <section className="rounded-2xl border border-line bg-card p-4">
              <h3 className="display font-semibold">Weather at {dest?.label ?? "destination"}</h3>
              <p className="mt-1 text-sm">
                {weather.observed.conditions}, {weather.observed.temperature_c}°C, wind{" "}
                {weather.observed.wind_speed_kmh} km/h <span className="text-xs text-ink-soft">(observed)</span>
              </p>
              {weather.derived.signals.length > 0 ? (
                <ul className="mt-2 space-y-1">
                  {weather.derived.signals.map((signal, i) => (
                    <li key={i} className="flex gap-2 text-sm text-watch">
                      <span>•</span>
                      <span>{signal} <span className="text-xs text-ink-soft">(derived estimate)</span></span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-1 text-xs text-ink-soft">No weather concerns for this trip right now.</p>
              )}
            </section>
          )}

          {preview.alerts.length > 0 && (
            <section className="space-y-3">
              <h3 className="display px-1 font-semibold">Things that may affect this journey</h3>
              {preview.alerts.map((alert) => (
                <AlertCard key={alert.id} alert={alert} />
              ))}
            </section>
          )}

          {(parking || parkingNote) && (
            <section className="rounded-2xl border border-line bg-card p-4">
              <h3 className="display font-semibold">Parking near {dest?.label ?? "destination"}</h3>
              {parkingNote && <p className="mt-1 text-sm text-ink-soft">{parkingNote}</p>}
              {parking && parking.length === 0 && (
                <p className="mt-1 text-sm text-ink-soft">No mapped parking within 800 m on OpenStreetMap.</p>
              )}
              <ul className="mt-2 space-y-3">
                {(parking ?? []).map((spot) => (
                  <li key={spot.id}>
                    <div className="flex items-baseline justify-between gap-2">
                      <p className="min-w-0 truncate text-sm font-medium">🅿️ {spot.name}</p>
                      <p className="shrink-0 text-xs text-ink-soft">{spot.distance_m} m</p>
                    </div>
                    <div className="mt-1 flex items-center gap-2">
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-line" role="presentation">
                        <div
                          className={`h-full rounded-full ${spot.probability.value_pct >= 60 ? "bg-pine" : spot.probability.value_pct >= 35 ? "bg-watch" : "bg-act"}`}
                          style={{ width: `${spot.probability.value_pct}%` }}
                        />
                      </div>
                      <span className="text-xs font-semibold tabular-nums">{spot.probability.value_pct}%</span>
                    </div>
                    <p className="text-[11px] text-ink-soft">
                      {spot.probability.label.toLowerCase()} — {spot.probability.reasons[0] ?? "no signals"}
                    </p>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
        );
      })()}
    </div>
  );
}
