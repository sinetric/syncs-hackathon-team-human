import { useCallback, useEffect, useState } from "react";
import { RequestError } from "../api/client";

/** Tiny fetch-state hook: every screen gets loading / error / reload for free. */
export function useFetch<T>(fetcher: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<RequestError | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetcher()
      .then((value) => {
        if (!cancelled) setData(value);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof RequestError ? err : new RequestError(0, "unknown", String(err)));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => reload(), [reload]);

  return { data, error, loading, reload };
}

export function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="animate-pulse space-y-3" aria-hidden="true">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="rounded-2xl border border-line bg-card p-4">
          <div className="mb-2 h-4 w-2/3 rounded bg-line" />
          <div className="h-3 w-full rounded bg-line/70" />
        </div>
      ))}
    </div>
  );
}

export function ErrorNote({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-2xl border border-act/30 bg-act-bg p-4">
      <p className="font-semibold text-act">Something went wrong</p>
      <p className="mt-1 text-sm text-ink-soft">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 rounded-lg border border-act/40 px-3 py-1.5 text-sm font-medium text-act"
        >
          Try again
        </button>
      )}
    </div>
  );
}

export function relativeTime(iso: string): string {
  const diffMin = Math.round((Date.now() - new Date(iso).getTime()) / 60_000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin} min ago`;
  return `${Math.round(diffMin / 60)} h ago`;
}

export function localHm(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-AU", { hour: "2-digit", minute: "2-digit", hour12: false });
}
