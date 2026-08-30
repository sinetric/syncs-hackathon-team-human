import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/client";
import type { MapFeature, MapFeatures } from "../api/types";
import FeatureMap, { FeatureCard, KIND_META, kindEmoji } from "../components/FeatureMap";
import { ErrorNote, Skeleton, relativeTime, useFetch } from "../components/common";

const FILTERS = [
  "transport_disruption", "incident", "roadwork", "construction", "weather", "venue", "parking",
] as const;
const RADII = [500, 1000, 2000, 5000];
const SYDNEY_CBD: [number, number] = [-33.8688, 151.2093];
const REFRESH_MS = 60_000;
const severityRank = (feature: MapFeature) =>
  feature.alert?.severity === "act" ? 0 : feature.alert?.severity === "watch" ? 1 : 2;

export default function MapScreen() {
  const places = useFetch(() => api.listPlaces());
  const [center, setCenter] = useState<[number, number] | null>(null);
  const [centerLabel, setCenterLabel] = useState("Sydney CBD");
  const [placeId, setPlaceId] = useState("");
  const [radiusM, setRadiusM] = useState(2000);
  const [enabled, setEnabled] = useState<Set<string>>(new Set(FILTERS));
  const [result, setResult] = useState<MapFeatures | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const [heroProgress, setHeroProgress] = useState(0);
  const storyRef = useRef<HTMLDivElement>(null);
  const cardsRef = useRef<HTMLDivElement>(null);
  const lastPlacesSyncRef = useRef(0);
  const initRef = useRef(false);

  const locateMe = useCallback((opts?: { silent?: boolean }) => {
    const fallback = () => { setCenter(SYDNEY_CBD); setCenterLabel("Sydney CBD"); };
    if (!navigator.geolocation) {
      if (opts?.silent) fallback();
      else setError("Location access isn't available in this browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setPlaceId("");
        setCenter([position.coords.latitude, position.coords.longitude]);
        setCenterLabel("your current location");
      },
      () => {
        if (opts?.silent) fallback();
        else setError("Location access was blocked. Choose a saved address instead.");
      },
      { timeout: 5000, maximumAge: 300_000 },
    );
  }, []);

  useEffect(() => {
    if (center || initRef.current) return;
    const data = places.data;
    if (data && data.length > 0) {
      initRef.current = true;
      const home = data.find((place) => /home/i.test(place.label)) ?? data[0];
      setCenter([home.lat, home.lng]);
      setCenterLabel(home.label);
      setPlaceId(home.id);
    } else if (!places.loading) {
      initRef.current = true;      // no saved places → start from the device location
      locateMe({ silent: true });
    }
  }, [places.data, places.loading, center, locateMe]);

  const load = useCallback(async (nextCenter: [number, number], radius: number) => {
    setLoading(true);
    setError(null);
    try {
      setResult(await api.mapFeatures({ lat: nextCenter[0], lng: nextCenter[1], radius_m: radius }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't load map data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!center) return;
    void load(center, radiusM);
    const interval = setInterval(() => void load(center, radiusM), REFRESH_MS);
    const ticker = setInterval(() => setTick((value) => value + 1), 15_000);
    return () => { clearInterval(interval); clearInterval(ticker); };
  }, [center, radiusM, load]);

  const visible = useMemo(
    () => (result?.data ?? [])
      .filter((feature) => enabled.has(feature.kind) || !FILTERS.includes(feature.kind as never))
      .sort((a, b) => severityRank(a) - severityRank(b)),
    [result, enabled],
  );

  useEffect(() => {
    if (!activeId || !visible.some((feature) => feature.id === activeId)) setActiveId(visible[0]?.id ?? null);
  }, [activeId, visible]);

  useEffect(() => {
    let frame = 0;
    const update = () => {
      frame = 0;
      const top = storyRef.current?.getBoundingClientRect().top ?? 0;
      setHeroProgress(Math.max(0, Math.min(1, (16 - top) / 180)));
    };
    const onScroll = () => { if (!frame) frame = requestAnimationFrame(update); };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => { window.removeEventListener("scroll", onScroll); if (frame) cancelAnimationFrame(frame); };
  }, []);

  useEffect(() => {
    const cards = cardsRef.current?.querySelectorAll<HTMLElement>("[data-feature-id]");
    if (!cards?.length) return;
    const observer = new IntersectionObserver((entries) => {
      const current = entries.filter((entry) => entry.isIntersecting)
        .sort((a, b) => Math.abs(a.boundingClientRect.top - innerHeight * 0.72) - Math.abs(b.boundingClientRect.top - innerHeight * 0.72))[0];
      const id = (current?.target as HTMLElement | undefined)?.dataset.featureId;
      if (id) setActiveId(id);
    }, { rootMargin: "-48% 0px -24% 0px", threshold: [0, 0.4, 0.8] });
    cards.forEach((card) => observer.observe(card));
    return () => observer.disconnect();
  }, [visible]);

  // Re-check saved Places when the "Map around" dropdown is opened, so a place
  // added on another screen shows up without a page refresh. Guarded so a single
  // click (mousedown + focus) doesn't fire two requests.
  const syncPlaces = () => {
    if (places.loading || Date.now() - lastPlacesSyncRef.current < 500) return;
    lastPlacesSyncRef.current = Date.now();
    places.reload();
  };

  if (!center) return <Skeleton lines={3} />;
  void tick;

  return (
    <div className="space-y-3">
      <div className="rounded-2xl border border-line bg-card p-3">
        <div className="flex gap-2">
          <label className="min-w-0 flex-1 text-xs font-semibold uppercase tracking-wide text-ink-soft">
            Map around
            <select
              value={placeId}
              onMouseDown={syncPlaces}
              onFocus={syncPlaces}
              onChange={(event) => {
                const place = (places.data ?? []).find((item) => item.id === event.target.value);
                if (!place) return;
                setPlaceId(place.id); setCenter([place.lat, place.lng]); setCenterLabel(place.label);
              }}
              className="mt-1 min-h-10 w-full rounded-xl border border-line bg-paper px-3 text-sm normal-case tracking-normal text-ink"
            >
              {!placeId && <option value="">Current location</option>}
              {(places.data ?? []).map((place) => <option key={place.id} value={place.id}>{place.label} — {place.address}</option>)}
            </select>
          </label>
          <label className="w-24 text-xs font-semibold uppercase tracking-wide text-ink-soft">
            Radius
            <select value={radiusM} onChange={(event) => setRadiusM(Number(event.target.value))}
              className="mt-1 min-h-10 w-full rounded-xl border border-line bg-paper px-2 text-sm normal-case tracking-normal text-ink" aria-label="Search radius">
              {RADII.map((radius) => <option key={radius} value={radius}>{radius < 1000 ? `${radius} m` : `${radius / 1000} km`}</option>)}
            </select>
          </label>
        </div>
        <button onClick={() => locateMe()} className="mt-2 min-h-9 rounded-lg px-2 text-xs font-medium text-pine">◎ Use my current location</button>
      </div>

      {error ? <ErrorNote message={error} onRetry={() => load(center, radiusM)} /> : (
        <div ref={storyRef} className="map-story relative pb-10">
          <div className="map-hero sticky top-2 z-10 origin-top transition-[transform,filter] duration-300 ease-out"
            style={{
              transform: `scale(${1 - heroProgress * 0.035}) translateY(${heroProgress * 4}px)`,
              filter: `drop-shadow(0 ${4 + heroProgress * 8}px ${8 + heroProgress * 14}px rgb(24 46 37 / ${0.08 + heroProgress * 0.12}))`,
            }}>
            <FeatureMap center={center} zoom={radiusM > 2000 ? 13 : radiusM > 900 ? 14 : 16}
              features={visible} radiusM={radiusM} heightClass="h-[58vh] min-h-96 max-h-[560px]"
              selectedFeatureId={activeId} onFeatureSelect={(feature) => setActiveId(feature.id)} />
            <div className="pointer-events-none absolute inset-x-3 top-3 flex items-center justify-between gap-2">
              <span className="rounded-full bg-card/90 px-3 py-1.5 text-xs font-semibold shadow-sm backdrop-blur">
                {loading ? "Scanning ahead…" : `${visible.length} obstacles around ${centerLabel}`}
              </span>
              <span className="rounded-full bg-pine px-2.5 py-1 text-[11px] font-semibold text-white shadow-sm">live map</span>
            </div>
          </div>

          <div ref={cardsRef} className="relative z-20 -mt-20 space-y-3 px-2 pt-[44vh]">
            {visible.map((feature, index) => (
              <article key={feature.id} data-feature-id={feature.id} tabIndex={0}
                onFocus={() => setActiveId(feature.id)} onClick={() => setActiveId(feature.id)}
                className={`map-story-card cursor-pointer rounded-2xl border bg-card/95 p-4 shadow-lg backdrop-blur transition-all duration-500 ${
                  activeId === feature.id ? "translate-y-0 border-pine ring-2 ring-pine/15" : "translate-y-1 border-line"
                }`}>
                <div className="mb-2 flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-pine">Ahead · {index + 1} of {visible.length}</p>
                    <h3 className="display mt-0.5 font-bold">{kindEmoji(feature.kind, feature.name)} {feature.name}</h3>
                  </div>
                  {feature.alert?.severity && (
                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold uppercase ${
                      feature.alert.severity === "act" ? "bg-act-bg text-act" : feature.alert.severity === "watch" ? "bg-watch-bg text-watch" : "bg-info-bg text-info"
                    }`}>{feature.alert.severity}</span>
                  )}
                </div>
                <FeatureCard feature={feature} showHeading={false} />
              </article>
            ))}
            {!loading && visible.length === 0 && (
              <div className="rounded-2xl border border-line bg-card p-5 text-center text-sm text-ink-soft shadow-lg">
                No mapped obstacles match these filters. Try a wider radius.
              </div>
            )}
          </div>
        </div>
      )}

      <div className="rounded-2xl border border-line bg-card p-3">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-soft">Show on map</p>
        <div className="flex flex-wrap gap-1.5">
          {FILTERS.map((kind) => {
            const on = enabled.has(kind);
            return <button key={kind} aria-pressed={on} onClick={() => setEnabled((previous) => {
              const next = new Set(previous); if (next.has(kind)) next.delete(kind); else next.add(kind); return next;
            })} className={`min-h-9 rounded-full border px-2.5 py-1 text-xs font-medium ${on ? "border-pine bg-pine-soft text-pine" : "border-line text-ink-soft opacity-60"}`}>
              {KIND_META[kind].emoji} {KIND_META[kind].label}
            </button>;
          })}
        </div>
        <p className="mt-2 text-xs text-ink-soft">
          {result ? `${visible.length} of ${result.data.length} features · updated ${relativeTime(result.fetched_at)}` : ""}
          {result && !result.overpass_available && <span className="block text-watch">OpenStreetMap is temporarily unavailable — alert obstacles are still shown.</span>}
        </p>
      </div>
    </div>
  );
}
