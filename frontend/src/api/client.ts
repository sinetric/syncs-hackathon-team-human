/**
 * The one typed API client. Every screen goes through here.
 *
 * VITE_API_BASE_URL  — backend origin (default http://localhost:8000)
 * VITE_USE_FIXTURES  — "true" renders the whole UI from local fixtures with
 *                      no backend running (for when the venue wifi dies).
 */

import {
  fixtureAlerts,
  fixtureJourney,
  fixtureMapFeatures,
  fixturePlaces,
  fixtureRoutines,
} from "./fixtures";
import type {
  Alert,
  ApiError,
  AskResponse,
  GeocodeResult,
  Health,
  JourneyPreview,
  MapFeatures,
  ParkingSpot,
  Place,
  PlaceCreate,
  Routine,
  RoutineCreate,
  TravelMode,
  Weather,
} from "./types";

const BASE = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000") + "/api/v1";
export const USE_FIXTURES = import.meta.env.VITE_USE_FIXTURES === "true";

export class RequestError extends Error {
  code: string;
  status: number;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let resp: Response;
  try {
    resp = await fetch(BASE + path, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
  } catch {
    throw new RequestError(0, "network", "Couldn't reach the server. Check it's running, or turn on fixtures mode.");
  }
  if (resp.status === 204) return undefined as T;
  const body = await resp.json().catch(() => null);
  if (!resp.ok) {
    const err = (body as ApiError | null)?.error;
    throw new RequestError(resp.status, err?.code ?? "http_error", err?.message ?? `Request failed (${resp.status})`);
  }
  return body as T;
}

// in-memory copies for fixtures mode so add/delete still feel real
let fxPlaces = [...fixturePlaces];
let fxRoutines = [...fixtureRoutines];
const fxDelay = () => new Promise((r) => setTimeout(r, 250));
const notifyPlacesChanged = () => {
  if (typeof window !== "undefined") window.dispatchEvent(new Event("knowahead:places-changed"));
};

function distanceM(aLat: number, aLng: number, bLat: number, bLng: number): number {
  const rad = (degrees: number) => degrees * Math.PI / 180;
  const dLat = rad(bLat - aLat);
  const dLng = rad(bLng - aLng);
  const value = Math.sin(dLat / 2) ** 2
    + Math.cos(rad(aLat)) * Math.cos(rad(bLat)) * Math.sin(dLng / 2) ** 2;
  return 6_371_000 * 2 * Math.atan2(Math.sqrt(value), Math.sqrt(1 - value));
}

export const api = {
  async health(): Promise<Health> {
    if (USE_FIXTURES) return { status: "ok", version: "fixtures", demo_mode: true };
    return request("/health");
  },

  async listPlaces(): Promise<Place[]> {
    if (USE_FIXTURES) return fxDelay().then(() => [...fxPlaces]);
    return (await request<{ data: Place[] }>("/places")).data;
  },

  async geocode(address: string): Promise<GeocodeResult> {
    if (USE_FIXTURES) {
      const match = fixturePlaces.find((place) =>
        place.address.toLowerCase().includes(address.trim().toLowerCase())
        || address.trim().toLowerCase().includes(place.address.toLowerCase()),
      );
      if (!match) throw new RequestError(404, "address_not_found", "Custom address lookup needs the backend running.");
      return { address: match.address, lat: match.lat, lng: match.lng, source: "Offline fixture" };
    }
    return request(`/geocode?address=${encodeURIComponent(address)}`);
  },

  async createPlace(payload: PlaceCreate): Promise<Place> {
    if (USE_FIXTURES) {
      const place = { ...payload, id: `plc_fx${Date.now()}` };
      fxPlaces.push(place);
      notifyPlacesChanged();
      return place;
    }
    const place = await request<Place>("/places", { method: "POST", body: JSON.stringify(payload) });
    notifyPlacesChanged();
    return place;
  },

  async deletePlace(id: string): Promise<void> {
    if (USE_FIXTURES) {
      fxPlaces = fxPlaces.filter((p) => p.id !== id);
      fxRoutines = fxRoutines.filter((r) => r.origin_id !== id && r.dest_id !== id);
      notifyPlacesChanged();
      return;
    }
    await request(`/places/${id}`, { method: "DELETE" });
    notifyPlacesChanged();
  },

  async listRoutines(): Promise<Routine[]> {
    if (USE_FIXTURES) return fxDelay().then(() => [...fxRoutines]);
    return (await request<{ data: Routine[] }>("/routines")).data;
  },

  async createRoutine(payload: RoutineCreate): Promise<Routine> {
    if (USE_FIXTURES) {
      const routine = { ...payload, id: `rtn_fx${Date.now()}` };
      fxRoutines.push(routine);
      return routine;
    }
    return request("/routines", { method: "POST", body: JSON.stringify(payload) });
  },

  async listAlerts(params?: { routine_id?: string; place_id?: string; window_mins?: number }): Promise<Alert[]> {
    if (USE_FIXTURES) return fxDelay().then(() => fixtureAlerts());
    const search = new URLSearchParams();
    if (params?.routine_id) search.set("routine_id", params.routine_id);
    if (params?.place_id) search.set("place_id", params.place_id);
    if (params?.window_mins) search.set("window_mins", String(params.window_mins));
    const qs = search.toString();
    return (await request<{ data: Alert[] }>(`/alerts${qs ? `?${qs}` : ""}`)).data;
  },

  async journeyPreview(params: {
    origin_id: string;
    dest_id: string;
    depart_at?: string;
    mode?: TravelMode;
  }): Promise<JourneyPreview> {
    if (USE_FIXTURES) return fxDelay().then(() => fixtureJourney(params.mode ?? "transit"));
    const search = new URLSearchParams({ origin_id: params.origin_id, dest_id: params.dest_id });
    if (params.depart_at) search.set("depart_at", params.depart_at);
    if (params.mode) search.set("mode", params.mode);
    return request(`/journeys/preview?${search.toString()}`);
  },

  // Live-data endpoints. These hit real upstreams (Overpass, Open-Meteo) even
  // in backend demo mode, so fixtures mode degrades honestly instead of
  // faking map/weather data.
  async mapFeatures(params: { lat: number; lng: number; radius_m?: number; kinds?: string[] }): Promise<MapFeatures> {
    if (USE_FIXTURES) {
      const radius = params.radius_m ?? 1500;
      const data = fixtureMapFeatures().filter((feature) =>
        distanceM(params.lat, params.lng, feature.lat, feature.lng) <= radius
        && (!params.kinds?.length || params.kinds.includes(feature.kind)),
      );
      return { data, overpass_available: true, fetched_at: new Date().toISOString() };
    }
    const search = new URLSearchParams({ lat: String(params.lat), lng: String(params.lng) });
    if (params.radius_m) search.set("radius_m", String(params.radius_m));
    if (params.kinds?.length) search.set("kinds", params.kinds.join(","));
    return request(`/map/features?${search.toString()}`);
  },

  async weather(lat: number, lng: number): Promise<Weather> {
    if (USE_FIXTURES) throw new RequestError(503, "weather_unavailable", "Weather needs the backend running.");
    return request(`/weather?lat=${lat}&lng=${lng}`);
  },

  async parking(params: { lat: number; lng: number; radius_m?: number }): Promise<{ data: ParkingSpot[]; fetched_at: string }> {
    if (USE_FIXTURES) throw new RequestError(503, "parking_unavailable", "Parking search needs the backend running.");
    const search = new URLSearchParams({ lat: String(params.lat), lng: String(params.lng) });
    if (params.radius_m) search.set("radius_m", String(params.radius_m));
    return request(`/parking?${search.toString()}`);
  },

  async ask(question: string, origin_id?: string, dest_id?: string): Promise<AskResponse> {
    if (USE_FIXTURES) throw new RequestError(503, "ask_unavailable", "Ask AI needs the backend running.");
    return request("/ask", {
      method: "POST",
      body: JSON.stringify({ question, origin_id: origin_id ?? null, dest_id: dest_id ?? null }),
    });
  },

  async demoSeed(): Promise<{ places: number; routines: number }> {
    if (USE_FIXTURES) return { places: 2, routines: 1 };
    return request("/demo/seed", { method: "POST" });
  },
};
