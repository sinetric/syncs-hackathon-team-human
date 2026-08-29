import type { ReactNode } from "react";
import { divIcon } from "leaflet";
import { Circle, MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import type { FeatureKind, MapFeature } from "../api/types";
import { localHm, relativeTime } from "./common";

export const KIND_META: Record<string, { emoji: string; label: string }> = {
  construction: { emoji: "🚧", label: "Construction" },
  roadwork: { emoji: "🛣️", label: "Roadwork" },
  venue: { emoji: "🎵", label: "Event venue" },
  transport_disruption: { emoji: "🚆", label: "Transport disruption" },
  incident: { emoji: "⚠️", label: "Incident" },
  weather: { emoji: "🌧️", label: "Weather risk" },
  parking: { emoji: "🅿️", label: "Parking" },
  advice: { emoji: "💡", label: "Advice" },
  reminder: { emoji: "⏰", label: "Reminder" },
};

export function kindEmoji(kind: FeatureKind, name?: string): string {
  if (kind === "weather" && name && /flood/i.test(name)) return "🌊";
  return KIND_META[kind]?.emoji ?? "⚠️";
}

export function pinIcon(kind: FeatureKind, opts?: { severity?: string; name?: string }) {
  const severityClass =
    opts?.severity === "act" ? " ka-pin--act" : opts?.severity === "watch" ? " ka-pin--watch" : "";
  return divIcon({
    className: "",
    html: `<div class="ka-pin${severityClass}">${kindEmoji(kind, opts?.name)}</div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    popupAnchor: [0, -14],
  });
}

export function labelIcon(text: string, variant: "origin" | "dest") {
  return divIcon({
    className: "",
    html: `<div class="ka-pin ka-pin--${variant}">${text}</div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    popupAnchor: [0, -14],
  });
}

function Row({ label, value }: { label: string; value: ReactNode }) {
  return (
    <p className="mt-0.5 text-xs">
      <span className="text-ink-soft">{label}: </span>
      {value ?? <span className="italic text-ink-soft">Information unavailable</span>}
    </p>
  );
}

/** Popup card for one map feature — shows what the source provides and says
 * "Information unavailable" for the rest; estimates are labelled. */
export function FeatureCard({ feature }: { feature: MapFeature }) {
  const alert = feature.alert;
  const meta = KIND_META[feature.kind] ?? { label: feature.kind, emoji: "⚠️" };
  const interesting = Object.entries(feature.tags ?? {}).filter(([k]) =>
    ["access", "fee", "capacity", "parking", "opening_hours", "operator", "construction", "maxstay"].includes(k),
  );
  return (
    <div className="min-w-52 max-w-64">
      <p className="display text-sm font-bold leading-snug">
        {kindEmoji(feature.kind, feature.name)} {feature.name}
      </p>
      <p className="text-xs font-medium text-ink-soft">{meta.label}</p>
      {alert ? (
        <>
          {alert.body && <p className="mt-1 text-xs">{alert.body}</p>}
          <Row label="Status" value={<span className="font-semibold uppercase">{alert.severity}</span>} />
          <Row label="Active" value={`${localHm(alert.valid_from)} – ${localHm(alert.valid_to)}`} />
          <Row
            label="Journey impact"
            value={
              alert.impact.delay_minutes != null
                ? `+${alert.impact.delay_minutes} min (estimate)`
                : undefined
            }
          />
          <Row label="Confidence" value={`${Math.round(alert.impact.confidence * 100)}% (model estimate)`} />
        </>
      ) : (
        <>
          {interesting.length > 0
            ? interesting.map(([k, v]) => <Row key={k} label={k.replace("_", " ")} value={v} />)
            : <Row label="Details" value={undefined} />}
        </>
      )}
      <p className="mt-1.5 border-t border-line pt-1 text-[10px] text-ink-soft">
        {feature.source.url ? (
          <a href={feature.source.url} target="_blank" rel="noreferrer" className="underline">
            {feature.source.name}
          </a>
        ) : (
          feature.source.name
        )}{" "}
        · updated {relativeTime(feature.source.fetched_at)}
      </p>
    </div>
  );
}

interface FeatureMapProps {
  center: [number, number];
  zoom?: number;
  features: MapFeature[];
  radiusM?: number;
  heightClass?: string;
  children?: ReactNode;
}

export default function FeatureMap({
  center,
  zoom = 15,
  features,
  radiusM,
  heightClass = "h-80",
  children,
}: FeatureMapProps) {
  return (
    <div className={`${heightClass} overflow-hidden rounded-2xl border border-line`}>
      <MapContainer center={center} zoom={zoom} className="h-full w-full" scrollWheelZoom>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {radiusM && (
          <Circle
            center={center}
            radius={radiusM}
            pathOptions={{ color: "#1e5c48", weight: 1, fillOpacity: 0.04, dashArray: "4 6" }}
          />
        )}
        {features.map((feature) => (
          <Marker
            key={feature.id}
            position={[feature.lat, feature.lng]}
            icon={pinIcon(feature.kind, { severity: feature.alert?.severity, name: feature.name })}
          >
            <Popup>
              <FeatureCard feature={feature} />
            </Popup>
          </Marker>
        ))}
        {children}
      </MapContainer>
    </div>
  );
}
