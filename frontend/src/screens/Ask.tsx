import { useState } from "react";
import { api } from "../api/client";
import type { AskResponse } from "../api/types";
import { useFetch } from "../components/common";

const SUGGESTIONS = [
  "What's happening around me?",
  "What could affect my journey?",
  "Should I leave earlier?",
  "Will the weather affect my trip?",
  "Where can I park near my destination?",
  "What's the biggest obstacle on my journey?",
];

const ENGINE_BADGE: Record<AskResponse["engine"], { label: string; cls: string }> = {
  huggingface_api: { label: "Qwen · Hugging Face", cls: "bg-pine-soft text-pine" },
  local_qwen: { label: "Qwen · local", cls: "bg-pine-soft text-pine" },
  rules: { label: "Rule-based (no AI model)", cls: "bg-watch-bg text-watch" },
};

export default function Ask() {
  const places = useFetch(() => api.listPlaces());
  const [question, setQuestion] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async (q: string) => {
    const trimmed = q.trim();
    if (!trimmed || pending) return;
    setPending(trimmed);
    setError(null);
    setResponse(null);
    try {
      // give the AI a journey when the user has one: first two saved places
      const data = places.data ?? [];
      const origin = data.find((p) => /home/i.test(p.label)) ?? data[0];
      const dest = data.find((p) => p.id !== origin?.id);
      setResponse(await api.ask(trimmed, origin?.id, dest?.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "The AI couldn't answer that. Try again.");
    } finally {
      setPending(null);
    }
  };

  return (
    <div className="space-y-4">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(question);
        }}
        className="rounded-2xl border border-line bg-card p-3"
      >
        <label htmlFor="ask-input" className="sr-only">Ask about your surroundings and journey</label>
        <div className="flex gap-2">
          <input
            id="ask-input"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask about your journey, weather, parking…"
            className="min-h-11 w-full rounded-xl border border-line bg-paper px-3 text-sm"
          />
          <button
            type="submit"
            disabled={!!pending || !question.trim()}
            className="min-h-11 shrink-0 rounded-xl bg-pine px-4 text-sm font-medium text-white disabled:opacity-50"
          >
            Ask
          </button>
        </div>
      </form>

      <div className="flex flex-wrap gap-1.5 px-1">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => {
              setQuestion(s);
              submit(s);
            }}
            disabled={!!pending}
            className="min-h-9 rounded-full border border-line bg-card px-3 py-1.5 text-xs text-ink-soft hover:border-pine hover:text-pine disabled:opacity-50"
          >
            {s}
          </button>
        ))}
      </div>

      {pending && (
        <div className="rounded-2xl border border-line bg-card p-4">
          <p className="text-sm font-medium">“{pending}”</p>
          <p className="mt-2 animate-pulse text-sm text-ink-soft">
            Gathering live alerts, weather and parking, then asking the model…
          </p>
        </div>
      )}

      {error && (
        <div role="alert" className="rounded-2xl border border-act/30 bg-act-bg p-4 text-sm">
          <p className="font-semibold text-act">That didn't work</p>
          <p className="mt-1 text-ink-soft">{error}</p>
        </div>
      )}

      {response && (
        <article className="rounded-2xl border border-line bg-card p-4">
          <div className="flex items-start justify-between gap-2">
            <h3 className="display font-bold">Answer</h3>
            <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${ENGINE_BADGE[response.engine].cls}`}>
              {ENGINE_BADGE[response.engine].label}
            </span>
          </div>
          <p className="mt-2 text-sm leading-relaxed">{response.answer}</p>

          {response.factors.length > 0 && (
            <div className="mt-3 rounded-xl bg-paper p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-ink-soft">Why</p>
              <ul className="mt-1.5 space-y-1">
                {response.factors.map((factor, i) => (
                  <li key={i} className="flex gap-2 text-sm">
                    <span className="text-pine">•</span>
                    <span>{factor}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <p className="mt-3 text-xs text-ink-soft">
            {response.confidence_pct != null && (
              <span className="font-medium">Confidence: {response.confidence_pct}% (model estimate) · </span>
            )}
            Based on: {response.context_used.join(", ") || "no live data"}
          </p>
          <p className="mt-1 text-xs italic text-ink-soft">{response.disclaimer}</p>
        </article>
      )}

      {!response && !pending && !error && (
        <p className="px-1 text-center text-sm text-ink-soft">
          Answers come from your live app data — alerts, weather, journey and parking — not a generic chatbot.
        </p>
      )}
    </div>
  );
}
