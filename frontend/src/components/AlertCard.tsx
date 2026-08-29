import { useEffect, useMemo, useState } from "react";
import type { Alert, Severity } from "../api/types";
import { localHm, relativeTime } from "./common";

/**
 * Severity is carried by type weight + border weight + a text tag, with colour
 * as reinforcement only — the hierarchy survives greyscale and colourblindness.
 */
const SEVERITY_STYLE: Record<Severity, { card: string; tag: string; label: string }> = {
  act: { card: "border-l-4 border-l-act", tag: "bg-act-bg text-act", label: "Act" },
  watch: { card: "border-l-[3px] border-l-watch", tag: "bg-watch-bg text-watch", label: "Watch" },
  info: { card: "border-l-2 border-l-info", tag: "bg-info-bg text-info", label: "FYI" },
};

const KIND_ICON: Record<string, string> = {
  transport_disruption: "M4 15V6a4 4 0 0 1 4-4h8a4 4 0 0 1 4 4v9a3 3 0 0 1-3 3l1.5 2v1h-2l-2-2.5h-5L7.5 21h-2v-1L7 18a3 3 0 0 1-3-3Zm4-11a2 2 0 0 0-2 2v3h12V6a2 2 0 0 0-2-2H8Zm-1 12.5A1.5 1.5 0 1 0 7 13.5a1.5 1.5 0 0 0 0 3Zm10 0a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z",
  roadwork: "M12 2 1 21h22L12 2Zm0 4.5L19.5 19h-15L12 6.5ZM11 10v4h2v-4h-2Zm0 6v2h2v-2h-2Z",
  incident: "M12 2 1 21h22L12 2Zm0 4.5L19.5 19h-15L12 6.5ZM11 10v4h2v-4h-2Zm0 6v2h2v-2h-2Z",
  weather: "M6 14a4 4 0 0 1 .5-7.97A5.5 5.5 0 0 1 17.2 7.6 3.8 3.8 0 0 1 17 15H6Zm2 3 1.2 2H7.8L9 17H8Zm4 0 1.2 2h-1.4L13 17h-1Zm4 0 1.2 2h-1.4L17 17h-1Z",
  construction: "M3 21v-2h18v2H3Zm2-4v-6h2v6H5Zm4 0V7h2v10H9Zm4 0v-8h2v8h-2Zm4 0V4h2v13h-2Z",
  reminder: "M12 2a7 7 0 0 1 7 7v4.6l1.8 3.4H3.2L5 13.6V9a7 7 0 0 1 7-7Zm-2.5 17h5a2.5 2.5 0 0 1-5 0Z",
  advice: "M12 2a8 8 0 0 1 4.9 14.3c-.6.5-.9 1-.9 1.7v1H8v-1c0-.7-.3-1.2-.9-1.7A8 8 0 0 1 12 2ZM9 21h6v1.5H9V21Z",
};

function Countdown({ target }: { target: string }) {
  const reduced = useMemo(
    () => window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    [],
  );
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), reduced ? 60_000 : 1000);
    return () => clearInterval(interval);
  }, [reduced]);

  const left = Math.max(0, new Date(target).getTime() - now);
  const m = Math.floor(left / 60_000);
  const s = Math.floor((left % 60_000) / 1000);
  return (
    <p className="display text-4xl font-bold tabular-nums tracking-tight" aria-live="off">
      {left === 0 ? "now" : reduced ? `${m} min` : `${m}:${String(s).padStart(2, "0")}`}
    </p>
  );
}

interface Props {
  alert: Alert;
  onReroute?: () => void;
}

export default function AlertCard({ alert, onReroute }: Props) {
  const [applied, setApplied] = useState<string | null>(null);
  const style = SEVERITY_STYLE[alert.severity];

  // Leave-now reminders get the signature treatment: the countdown is the
  // only thing on screen that changes while you look at it.
  if (alert.kind === "reminder") {
    return (
      <article className={`rounded-2xl border border-line bg-pine p-4 text-white ${alert.severity === "act" ? "" : "opacity-95"}`}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-white/70">Leave in</p>
            <Countdown target={alert.valid_to} />
          </div>
          <span className="rounded-full bg-white/15 px-2 py-0.5 text-xs font-semibold">
            {style.label}
          </span>
        </div>
        <h3 className="display mt-2 font-semibold">{alert.title}</h3>
        <p className="mt-1 text-sm text-white/80">{alert.body}</p>
        {applied && <p className="mt-2 text-sm font-medium text-white">{applied}</p>}
        {!applied &&
          alert.actions.map((action) => (
            <button
              key={action.type}
              onClick={() => setApplied("Done — you'll get a nudge 10 min before.")}
              className="mt-3 rounded-xl bg-white/15 px-3 py-2 text-sm font-medium"
            >
              {action.label}
            </button>
          ))}
      </article>
    );
  }

  const delay = alert.impact.delay_minutes;

  return (
    <article className={`rounded-2xl border border-line bg-card p-4 ${style.card}`}>
      <div className="flex items-start gap-3">
        <svg viewBox="0 0 24 24" className="mt-0.5 h-5 w-5 shrink-0 text-ink-soft" aria-hidden="true">
          <path fill="currentColor" d={KIND_ICON[alert.kind] ?? KIND_ICON.advice} />
        </svg>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <h3 className={`display leading-snug ${alert.severity === "act" ? "text-lg font-bold" : alert.severity === "watch" ? "font-semibold" : "font-medium text-ink-soft"}`}>
              {alert.title}
            </h3>
            <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${style.tag}`}>
              {style.label}
            </span>
          </div>
          <p className="mt-1 text-sm text-ink-soft">{alert.body}</p>
          {delay != null && (
            <p className="mt-2 text-sm font-semibold">
              +{delay} min{" "}
              {alert.affects.routine_ids.length || alert.affects.leg_index != null
                ? "on your trip"
                : "in the area"}
              <span className="ml-1 font-normal text-ink-soft">
                · {Math.round(alert.impact.confidence * 100)}% confidence
              </span>
            </p>
          )}
          {applied ? (
            <p className="mt-3 rounded-xl bg-pine-soft px-3 py-2 text-sm font-medium text-pine">{applied}</p>
          ) : (
            alert.actions.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {alert.actions.map((action) => (
                  <button
                    key={action.type}
                    onClick={() => {
                      if (action.type === "leave_earlier") {
                        const mins = Number(action.payload.minutes ?? 0);
                        setApplied(`Plan updated — leaving ${mins} min earlier today.`);
                      } else if (action.type === "reroute") {
                        onReroute?.();
                      }
                    }}
                    className={`min-h-10 rounded-xl px-3 py-2 text-sm font-medium ${
                      action.type === "leave_earlier"
                        ? "bg-pine text-white"
                        : "border border-line bg-card text-ink"
                    }`}
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            )
          )}
          <p className="mt-3 text-xs text-ink-soft">
            {alert.source.url ? (
              <a href={alert.source.url} target="_blank" rel="noreferrer" className="underline decoration-line underline-offset-2">
                {alert.source.name}
              </a>
            ) : (
              alert.source.name
            )}{" "}
            · fetched {relativeTime(alert.source.fetched_at)} · until {localHm(alert.valid_to)}
          </p>
        </div>
      </div>
    </article>
  );
}
