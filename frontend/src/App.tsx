import { useEffect, useState } from "react";
import { USE_FIXTURES } from "./api/client";
import Today from "./screens/Today";
import Journey from "./screens/Journey";
import Places from "./screens/Places";
import More from "./screens/More";

export type Tab = "today" | "journey" | "places" | "more";

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: "today", label: "Today", icon: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm.75 5v5.19l3.53 2.12-.77 1.28L11.25 13V7h1.5Z" },
  { id: "journey", label: "Journey", icon: "M17 3a4 4 0 0 1 4 4c0 2.5-4 7-4 7s-4-4.5-4-7a4 4 0 0 1 4-4Zm0 2.5A1.5 1.5 0 1 0 17 8.5a1.5 1.5 0 0 0 0-3ZM7 12c2 0 4 1.6 4 4s-4 6-4 6-4-3.6-4-6 2-4 4-4Zm0 2.5A1.5 1.5 0 1 0 7 17.5a1.5 1.5 0 0 0 0-3Z" },
  { id: "places", label: "Places", icon: "M12 3 3 10h2v10h5v-6h4v6h5V10h2L12 3Z" },
  { id: "more", label: "More", icon: "M5 10.5a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3Zm7 0a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3Zm7 0a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3Z" },
];

function tabFromHash(): Tab {
  const hash = window.location.hash.replace("#/", "");
  return (TABS.some((t) => t.id === hash) ? hash : "today") as Tab;
}

export default function App() {
  const [tab, setTab] = useState<Tab>(tabFromHash);

  useEffect(() => {
    const onHash = () => setTab(tabFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const go = (next: Tab) => {
    window.location.hash = `/${next}`;
  };

  return (
    <div className="mx-auto flex min-h-dvh max-w-[430px] flex-col bg-paper">
      <header className="flex items-baseline justify-between px-5 pb-3 pt-6">
        <h1 className="display text-2xl font-bold tracking-tight text-pine">Know Ahead</h1>
        {USE_FIXTURES && (
          <span className="rounded-full bg-pine-soft px-2 py-0.5 text-xs font-medium text-pine">
            fixtures
          </span>
        )}
      </header>

      <main className="flex-1 px-4 pb-24">
        {tab === "today" && <Today goJourney={() => go("journey")} goPlaces={() => go("places")} />}
        {tab === "journey" && <Journey />}
        {tab === "places" && <Places />}
        {tab === "more" && <More />}
      </main>

      <nav
        aria-label="Main"
        className="fixed inset-x-0 bottom-0 mx-auto max-w-[430px] border-t border-line bg-card/95 backdrop-blur"
      >
        <ul className="flex">
          {TABS.map((t) => (
            <li key={t.id} className="flex-1">
              <button
                onClick={() => go(t.id)}
                aria-current={tab === t.id ? "page" : undefined}
                className={`flex min-h-14 w-full flex-col items-center justify-center gap-0.5 text-xs ${
                  tab === t.id ? "font-semibold text-pine" : "text-ink-soft"
                }`}
              >
                <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden="true">
                  <path fill="currentColor" d={t.icon} />
                </svg>
                {t.label}
              </button>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
