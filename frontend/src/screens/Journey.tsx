import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { JourneyPreview, LegMode, TravelMode } from "../api/types";
import AlertCard from "../components/AlertCard";
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

      {preview && !previewLoading && (
        <>
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

          {preview.alerts.length > 0 && (
            <section className="space-y-3">
              <h3 className="display px-1 font-semibold">On this journey</h3>
              {preview.alerts.map((alert) => (
                <AlertCard key={alert.id} alert={alert} />
              ))}
            </section>
          )}
        </>
      )}
    </div>
  );
}
