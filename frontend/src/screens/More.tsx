const PARKED = [
  { label: "Ticket photo wallet", note: "Snap your paper ticket, find it at the gate" },
  { label: "Carriage position", note: "Board where the exit will be" },
  { label: "Interstate parking rules", note: "Kerb sign decoder for unfamiliar cities" },
  { label: "Fare caps", note: "Know when the rest of the week rides free" },
  { label: "Security screening", note: "What to expect at big venues and airports" },
];

export default function More() {
  return (
    <div>
      <h2 className="display px-1 text-lg font-bold">Coming soon</h2>
      <p className="mt-1 px-1 text-sm text-ink-soft">
        On the roadmap, not in today's build. Mostly static reference data — cheap to add.
      </p>
      <ul className="mt-3 space-y-2" aria-label="Planned features">
        {PARKED.map((item) => (
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
    </div>
  );
}
