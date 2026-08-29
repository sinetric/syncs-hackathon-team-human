import { useState } from "react";
import { api } from "../api/client";
import AlertCard from "../components/AlertCard";
import { ErrorNote, Skeleton, useFetch } from "../components/common";

interface Props {
  goJourney: () => void;
  goPlaces: () => void;
}

export default function Today({ goJourney, goPlaces }: Props) {
  const [seeding, setSeeding] = useState(false);
  const alerts = useFetch(() => api.listAlerts({ window_mins: 180 }));
  const routines = useFetch(() => api.listRoutines());

  const seedDemo = async () => {
    setSeeding(true);
    try {
      await api.demoSeed();
      alerts.reload();
      routines.reload();
    } finally {
      setSeeding(false);
    }
  };

  if (alerts.loading) return <Skeleton lines={4} />;
  if (alerts.error)
    return <ErrorNote message={alerts.error.message} onRetry={alerts.reload} />;

  const list = alerts.data ?? [];

  if (list.length === 0) {
    const hasRoutines = (routines.data?.length ?? 0) > 0;
    return (
      <div className="mt-16 text-center">
        <h2 className="display text-xl font-bold">Nothing in your way today.</h2>
        <p className="mx-auto mt-2 max-w-64 text-sm text-ink-soft">
          {hasRoutines
            ? "Your routes are clear. Check back before you leave."
            : "Add a routine and Know Ahead will tell you what changed before you leave."}
        </p>
        <div className="mt-6 flex flex-col items-center gap-2">
          {!hasRoutines && (
            <button
              onClick={goPlaces}
              className="min-h-11 rounded-xl bg-pine px-5 py-2.5 font-medium text-white"
            >
              Add a routine
            </button>
          )}
          <button
            onClick={seedDemo}
            disabled={seeding}
            className="min-h-11 rounded-xl border border-line px-5 py-2.5 text-sm font-medium text-ink-soft"
          >
            {seeding ? "Loading demo data…" : "Load demo data"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="px-1 text-sm text-ink-soft">
        {list.length} heads-up{list.length === 1 ? "" : "s"} for the next 3 hours
      </p>
      {list.map((alert) => (
        <AlertCard key={alert.id} alert={alert} onReroute={goJourney} />
      ))}
    </div>
  );
}
