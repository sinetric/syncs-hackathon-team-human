import { useState } from "react";
import { api } from "../api/client";
import type { TravelMode, Weekday } from "../api/types";
import { ErrorNote, Skeleton, useFetch } from "../components/common";

const DAYS: Weekday[] = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

// Setup has to be fast — a few one-tap presets cover the demo and most of Sydney.
const PRESETS = [
  { label: "Home", address: "12 Illawarra Rd, Marrickville NSW", lat: -33.911, lng: 151.1554 },
  { label: "Uni", address: "15 Broadway, Ultimo NSW", lat: -33.8836, lng: 151.1997 },
  { label: "Work", address: "1 Martin Pl, Sydney NSW", lat: -33.8679, lng: 151.2093 },
];

const inputClass = "min-h-11 w-full rounded-xl border border-line bg-card px-3 py-2 text-sm";

export default function Places() {
  const places = useFetch(() => api.listPlaces());
  const routines = useFetch(() => api.listRoutines());
  const [busy, setBusy] = useState(false);
  const [locating, setLocating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // add-place form
  const [label, setLabel] = useState("");
  const [address, setAddress] = useState("");

  // add-routine form
  const [rtnName, setRtnName] = useState("");
  const [rtnOrigin, setRtnOrigin] = useState("");
  const [rtnDest, setRtnDest] = useState("");
  const [rtnDays, setRtnDays] = useState<Set<Weekday>>(new Set(["mon", "tue", "wed", "thu", "fri"]));
  const [rtnTime, setRtnTime] = useState("07:40");
  const [rtnMode, setRtnMode] = useState<TravelMode>("transit");

  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setFormError(null);
    try {
      await fn();
      places.reload();
      routines.reload();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "That didn't save. Try again.");
    } finally {
      setBusy(false);
    }
  };

  // Save the device's current position as a place. No street address is
  // available client-side, so we label it plainly and store the coordinates.
  const addCurrentLocation = () => {
    if (!navigator.geolocation) {
      setFormError("Location access isn't available in this browser.");
      return;
    }
    setLocating(true);
    setFormError(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords;
        setLocating(false);
        void run(() =>
          api.createPlace({
            label: "Current location",
            address: `Near ${latitude.toFixed(4)}, ${longitude.toFixed(4)}`,
            lat: latitude,
            lng: longitude,
          }),
        );
      },
      () => {
        setLocating(false);
        setFormError("Location access was blocked. Enter an address instead.");
      },
      { timeout: 5000, maximumAge: 300_000 },
    );
  };

  const addPlace = () =>
    run(async () => {
      if (!label.trim() || !address.trim()) throw new Error("Give the place a name and street address.");
      const resolved = await api.geocode(address.trim());
      await api.createPlace({ label: label.trim(), address: resolved.address, lat: resolved.lat, lng: resolved.lng });
      setLabel(""); setAddress("");
    });

  const addRoutine = () =>
    run(async () => {
      if (!rtnName.trim()) throw new Error("Give the routine a name, like “Uni run”.");
      if (!rtnOrigin || !rtnDest || rtnOrigin === rtnDest) throw new Error("Pick two different places.");
      if (rtnDays.size === 0) throw new Error("Pick at least one day.");
      await api.createRoutine({
        name: rtnName.trim(),
        origin_id: rtnOrigin,
        dest_id: rtnDest,
        days: DAYS.filter((d) => rtnDays.has(d)),
        depart_local_time: rtnTime,
        mode: rtnMode,
      });
      setRtnName("");
    });

  if (places.loading || routines.loading) return <Skeleton lines={4} />;
  if (places.error) return <ErrorNote message={places.error.message} onRetry={places.reload} />;

  const placeList = places.data ?? [];
  const routineList = routines.data ?? [];
  const placeName = (id: string) => placeList.find((p) => p.id === id)?.label ?? "a deleted place";

  return (
    <div className="space-y-5">
      <section>
        <h2 className="display px-1 text-lg font-bold">Places</h2>
        {placeList.length === 0 && (
          <p className="mt-1 px-1 text-sm text-ink-soft">Save the places you leave from and go to.</p>
        )}
        <ul className="mt-2 space-y-2">
          {placeList.map((place) => (
            <li key={place.id} className="flex items-center gap-3 rounded-2xl border border-line bg-card px-4 py-3">
              <div className="min-w-0 flex-1">
                <p className="font-semibold">{place.label}</p>
                <p className="truncate text-xs text-ink-soft">{place.address}</p>
              </div>
              <button
                onClick={() => run(() => api.deletePlace(place.id))}
                disabled={busy}
                className="min-h-10 rounded-lg px-3 text-sm font-medium text-act"
                aria-label={`Delete ${place.label}`}
              >
                Delete
              </button>
            </li>
          ))}
        </ul>

        <div className="mt-3 rounded-2xl border border-line bg-card p-4">
          <div className="flex flex-wrap gap-2">
            {!placeList.some((p) => p.label === "Current location") && (
              <button
                onClick={addCurrentLocation}
                disabled={busy || locating}
                className="min-h-10 rounded-xl bg-pine-soft px-3 py-1.5 text-sm font-medium text-pine"
              >
                {locating ? "Locating…" : "◎ Current location"}
              </button>
            )}
            {PRESETS.filter((preset) => !placeList.some((p) => p.label === preset.label)).map((preset) => (
              <button
                key={preset.label}
                onClick={() => run(() => api.createPlace(preset))}
                disabled={busy}
                className="min-h-10 rounded-xl bg-pine-soft px-3 py-1.5 text-sm font-medium text-pine"
              >
                + {preset.label}
              </button>
            ))}
          </div>
          <div className="mt-3 space-y-2">
            <input placeholder="Name (e.g. Gym)" value={label} onChange={(e) => setLabel(e.target.value)} className={inputClass} />
            <input placeholder="Street address, suburb or postcode" value={address} onChange={(e) => setAddress(e.target.value)} className={inputClass} autoComplete="street-address" />
            <p className="px-1 text-xs text-ink-soft">We'll find the map location from the address when you save. © OpenStreetMap contributors.</p>
          </div>
          <button onClick={addPlace} disabled={busy} className="mt-3 min-h-11 w-full rounded-xl border border-pine font-medium text-pine">
            {busy ? "Finding address…" : "Find address & save"}
          </button>
        </div>
      </section>

      <section>
        <h2 className="display px-1 text-lg font-bold">Routines</h2>
        <ul className="mt-2 space-y-2">
          {routineList.map((routine) => (
            <li key={routine.id} className="rounded-2xl border border-line bg-card px-4 py-3">
              <p className="font-semibold">{routine.name}</p>
              <p className="text-xs text-ink-soft">
                {placeName(routine.origin_id)} → {placeName(routine.dest_id)} · {routine.depart_local_time} ·{" "}
                {routine.days.join(" ")} · {routine.mode}
              </p>
            </li>
          ))}
        </ul>

        {placeList.length >= 2 ? (
          <div className="mt-3 rounded-2xl border border-line bg-card p-4">
            <input placeholder="Name (e.g. Uni run)" value={rtnName} onChange={(e) => setRtnName(e.target.value)} className={inputClass} />
            <div className="mt-2 grid grid-cols-2 gap-2">
              <select value={rtnOrigin} onChange={(e) => setRtnOrigin(e.target.value)} className={inputClass} aria-label="From">
                <option value="">From…</option>
                {placeList.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
              </select>
              <select value={rtnDest} onChange={(e) => setRtnDest(e.target.value)} className={inputClass} aria-label="To">
                <option value="">To…</option>
                {placeList.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
              </select>
              <input type="time" value={rtnTime} onChange={(e) => setRtnTime(e.target.value)} className={inputClass} aria-label="Departure time" />
              <select value={rtnMode} onChange={(e) => setRtnMode(e.target.value as TravelMode)} className={inputClass} aria-label="Mode">
                <option value="transit">Transit</option>
                <option value="drive">Drive</option>
                <option value="walk">Walk</option>
              </select>
            </div>
            <div className="mt-2 flex gap-1" role="group" aria-label="Days of the week">
              {DAYS.map((day) => (
                <button
                  key={day}
                  onClick={() =>
                    setRtnDays((prev) => {
                      const next = new Set(prev);
                      if (next.has(day)) next.delete(day);
                      else next.add(day);
                      return next;
                    })
                  }
                  aria-pressed={rtnDays.has(day)}
                  className={`min-h-10 flex-1 rounded-lg text-xs font-medium capitalize ${
                    rtnDays.has(day) ? "bg-pine text-white" : "border border-line text-ink-soft"
                  }`}
                >
                  {day}
                </button>
              ))}
            </div>
            <button onClick={addRoutine} disabled={busy} className="mt-3 min-h-11 w-full rounded-xl bg-pine font-medium text-white">
              Save routine
            </button>
          </div>
        ) : (
          <p className="mt-2 px-1 text-sm text-ink-soft">Save two places and the routine form appears here.</p>
        )}
      </section>

      {formError && <ErrorNote message={formError} />}

      <section>
        <h2 className="display px-1 text-lg font-bold">Coming soon</h2>
        <ul className="mt-2 space-y-2" aria-label="Planned features">
          {[
            { label: "Ticket photo wallet", note: "Snap your paper ticket, find it at the gate" },
            { label: "Carriage position", note: "Board where the exit will be" },
            { label: "Interstate parking rules", note: "Kerb sign decoder for unfamiliar cities" },
            { label: "Fare caps", note: "Know when the rest of the week rides free" },
            { label: "Security screening", note: "What to expect at big venues and airports" },
          ].map((item) => (
            <li
              key={item.label}
              aria-disabled="true"
              className="flex items-center gap-3 rounded-2xl border border-line bg-card px-4 py-3 opacity-55"
            >
              <div className="min-w-0 flex-1">
                <p className="font-medium">{item.label}</p>
                <p className="text-xs text-ink-soft">{item.note}</p>
              </div>
              <span className="shrink-0 rounded-full bg-info-bg px-2 py-0.5 text-xs font-medium text-info">
                coming soon
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
