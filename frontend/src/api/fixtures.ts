/**
 * Fixtures mode — the whole UI renders from this file with no backend
 * running. Toggle with VITE_USE_FIXTURES=true (see client.ts). Times are
 * generated relative to "now" so the demo works on any day at any hour.
 */

import type { Alert, JourneyPreview, Place, Routine } from "./types";

const mins = (n: number) => new Date(Date.now() + n * 60_000).toISOString();
const hhmm = (n: number) =>
  new Date(Date.now() + n * 60_000).toLocaleTimeString("en-AU", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

export const fixturePlaces: Place[] = [
  { id: "plc_home", label: "Home", address: "12 Illawarra Rd, Marrickville NSW", lat: -33.911, lng: 151.1554 },
  { id: "plc_uni", label: "Uni", address: "15 Broadway, Ultimo NSW", lat: -33.8836, lng: 151.1997 },
];

export const fixtureRoutines: Routine[] = [
  {
    id: "rtn_uni",
    name: "Uni run",
    origin_id: "plc_home",
    dest_id: "plc_uni",
    days: ["mon", "tue", "wed", "thu", "fri"],
    depart_local_time: hhmm(45),
    mode: "transit",
  },
];

export function fixtureAlerts(): Alert[] {
  return [
    {
      id: "alt_reminder",
      kind: "reminder",
      severity: "act",
      title: `Leave by ${hhmm(33)} for your uni run`,
      body: `Delays add 12 min to your uni run. Leave by ${hhmm(33)} instead of ${hhmm(45)}.`,
      impact: { delay_minutes: 12, confidence: 0.8 },
      affects: { routine_ids: ["rtn_uni"], place_ids: [], leg_index: null },
      valid_from: mins(0),
      valid_to: mins(33),
      geo: null,
      actions: [
        { type: "leave_earlier", label: "Remind me 10 min before", payload: { minutes: 10, leave_at: mins(33) } },
      ],
      source: { name: "Know Ahead", url: null, fetched_at: mins(0) },
    },
    {
      id: "alt_t3",
      kind: "transport_disruption",
      severity: "act",
      title: "T3 trains delayed up to 12 min",
      body: "Signal repairs at Sydenham. Affects your uni run.",
      impact: { delay_minutes: 12, confidence: 0.72 },
      affects: { routine_ids: ["rtn_uni"], place_ids: [], leg_index: 1 },
      valid_from: mins(-60),
      valid_to: mins(240),
      geo: { lat: -33.9142, lng: 151.1697, radius_m: 600 },
      actions: [
        { type: "leave_earlier", label: "Leave 12 min earlier", payload: { minutes: 12 } },
        { type: "reroute", label: "Show alternative", payload: {} },
      ],
      source: { name: "Transport for NSW", url: "https://transportnsw.info/alerts", fetched_at: mins(-2) },
    },
    {
      id: "alt_broadway",
      kind: "roadwork",
      severity: "watch",
      title: "Footpath and lane closure on Broadway",
      body: "Crane work near Mountain St. Southern footpath closed, pedestrian detour in place. Affects your uni run.",
      impact: { delay_minutes: 5, confidence: 0.6 },
      affects: { routine_ids: ["rtn_uni"], place_ids: ["plc_uni"], leg_index: null },
      valid_from: mins(-180),
      valid_to: mins(2880),
      geo: { lat: -33.8842, lng: 151.1952, radius_m: 300 },
      actions: [{ type: "reroute", label: "Show alternative", payload: {} }],
      source: { name: "Live Traffic NSW", url: "https://www.livetraffic.com", fetched_at: mins(-2) },
    },
    {
      id: "alt_rain",
      kind: "weather",
      severity: "watch",
      title: "Rain likely near Uni (75%)",
      body: "75% chance of rain this evening around Broadway. An umbrella beats a wet walk home.",
      impact: { delay_minutes: null, confidence: 0.7 },
      affects: { routine_ids: ["rtn_uni"], place_ids: ["plc_uni"], leg_index: null },
      valid_from: mins(60),
      valid_to: mins(300),
      geo: { lat: -33.8836, lng: 151.1997, radius_m: 3000 },
      actions: [],
      source: { name: "Open-Meteo", url: "https://open-meteo.com", fetched_at: mins(-2) },
    },
    {
      id: "alt_da",
      kind: "construction",
      severity: "info",
      title: "6-storey apartment block approved 200 m from Home",
      body: "DA-2026/01187: demolition and construction of a 6-storey residential building with basement parking on Illawarra Rd.",
      impact: { delay_minutes: null, confidence: 0.6 },
      affects: { routine_ids: [], place_ids: ["plc_home"], leg_index: null },
      valid_from: mins(-43200),
      valid_to: mins(525600),
      geo: { lat: -33.9095, lng: 151.154, radius_m: 400 },
      actions: [],
      source: { name: "NSW Planning Portal", url: "https://www.planningportal.nsw.gov.au", fetched_at: mins(-2) },
    },
  ];
}

export function fixtureJourney(): JourneyPreview {
  const leg = (index: number, mode: JourneyLegMode, from: string, to: string, start: number, dur: number, line: string | null) => ({
    index,
    mode,
    from,
    to,
    depart_at: mins(start),
    arrive_at: mins(start + dur),
    line,
    duration_minutes: dur,
  });
  type JourneyLegMode = "walk" | "train" | "bus" | "lightrail" | "ferry" | "drive";
  return {
    duration_minutes: 74,
    trip_mode: "long",
    legs: [
      leg(0, "walk", "Home", "Marrickville Station", 0, 8, null),
      leg(1, "bus", "Marrickville Station", "Sydenham", 8, 22, "T3 rail replacement"),
      leg(2, "train", "Sydenham", "Central", 30, 18, "T4"),
      leg(3, "walk", "Central", "Uni", 48, 14, null),
    ],
    fare: { currency: "AUD", estimate_cents: 294, basis: "opal_adult_offpeak" },
    checklist: [
      { id: "chk_ticket", label: "Opal card or contactless", reason: "Transit legs on this trip" },
      { id: "chk_umbrella", label: "Umbrella", reason: "Rain is likely along the way" },
      { id: "chk_water", label: "Water bottle", reason: "74 min trip" },
      { id: "chk_toilet", label: "Bathroom before you go", reason: "Long trip — interchange stops have toilets" },
      { id: "chk_charge", label: "Phone charged", reason: "You'll want live updates en route" },
    ],
    alerts: fixtureAlerts().filter((a) => a.kind === "transport_disruption"),
  };
}
