/**
 * Hand-written against docs/api-contract.md — the single source of truth.
 * Do not add a field here that the contract doesn't have.
 */

export type TravelMode = "transit" | "drive" | "walk";
export type Weekday = "mon" | "tue" | "wed" | "thu" | "fri" | "sat" | "sun";

export interface Place {
  id: string;
  label: string;
  address: string;
  lat: number;
  lng: number;
}

export interface PlaceCreate {
  label: string;
  address: string;
  lat: number;
  lng: number;
}

export interface Routine {
  id: string;
  name: string;
  origin_id: string;
  dest_id: string;
  days: Weekday[];
  depart_local_time: string; // "HH:MM"
  mode: TravelMode;
}

export interface RoutineCreate {
  name: string;
  origin_id: string;
  dest_id: string;
  days: Weekday[];
  depart_local_time: string;
  mode: TravelMode;
}

export type AlertKind =
  | "transport_disruption"
  | "roadwork"
  | "incident"
  | "weather"
  | "construction"
  | "reminder"
  | "advice";

export type Severity = "info" | "watch" | "act";

export interface Alert {
  id: string;
  kind: AlertKind;
  severity: Severity;
  title: string;
  body: string;
  impact: { delay_minutes: number | null; confidence: number };
  affects: { routine_ids: string[]; place_ids: string[]; leg_index: number | null };
  valid_from: string;
  valid_to: string;
  geo: { lat: number; lng: number; radius_m: number } | null;
  actions: { type: string; label: string; payload: Record<string, unknown> }[];
  source: { name: string; url: string | null; fetched_at: string };
}

export type LegMode = "walk" | "train" | "bus" | "lightrail" | "ferry" | "drive";

export interface JourneyLeg {
  index: number;
  mode: LegMode;
  from: string;
  to: string;
  depart_at: string;
  arrive_at: string;
  line: string | null;
  duration_minutes: number;
}

export interface JourneyPreview {
  duration_minutes: number;
  trip_mode: "long" | "short";
  legs: JourneyLeg[];
  fare: { currency: string; estimate_cents: number; basis: string };
  checklist: { id: string; label: string; reason: string }[];
  alerts: Alert[];
}

export interface Health {
  status: string;
  version: string;
  demo_mode: boolean;
}

export interface ApiError {
  error: { code: string; message: string };
}

export type FeatureKind =
  | "parking"
  | "construction"
  | "roadwork"
  | "venue"
  | AlertKind;

export interface MapFeature {
  id: string;
  kind: FeatureKind;
  name: string;
  lat: number;
  lng: number;
  tags: Record<string, string>;
  alert?: Alert;
  source: { name: string; url: string | null; fetched_at: string };
}

export interface MapFeatures {
  data: MapFeature[];
  overpass_available: boolean;
  fetched_at: string;
}

export interface Weather {
  observed: {
    temperature_c: number | null;
    precipitation_mm: number | null;
    rain_mm: number | null;
    wind_speed_kmh: number | null;
    wind_gusts_kmh: number | null;
    weather_code: number | null;
    conditions: string;
  };
  derived: {
    raining_now: boolean;
    max_rain_probability_12h_pct: number | null;
    max_wind_gust_12h_kmh: number | null;
    signals: string[];
    basis: string;
  };
  source: { name: string; url: string; fetched_at: string };
}

export interface ParkingSpot extends MapFeature {
  distance_m: number;
  probability: {
    value_pct: number;
    label: string;
    basis: string;
    reasons: string[];
  };
}

export interface AskResponse {
  answer: string;
  factors: string[];
  confidence_pct: number | null;
  engine: "huggingface_api" | "local_qwen" | "rules";
  model: string | null;
  disclaimer: string;
  context_used: string[];
}
