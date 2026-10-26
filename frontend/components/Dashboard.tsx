"use client";

import { useEffect, useRef, useState } from "react";
import { Achievements } from "./Achievements";
import { CheckLog } from "./CheckLog";
import { Footer } from "./Footer";
import { Header } from "./Header";
import { IncidentPanel } from "./IncidentPanel";
import { KpiStrip } from "./KpiStrip";
import { LatencyChart } from "./LatencyChart";
import { Leaderboard } from "./Leaderboard";
import { DashboardSkeleton, EmptyState, ErrorState } from "./States";
import { loadDashboard, type Dashboard as DashboardData } from "@/lib/api";

const REFRESH_MS = 60_000;
// Once the countdown hits zero, look for the new sweep every 10s instead of waiting for the
// next 60s tick. Gives up after 2 minutes so a dead scheduler doesn't cause endless polling.
const OVERDUE_POLL_MS = 10_000;
const OVERDUE_GRACE_MS = 5_000;
const OVERDUE_GIVE_UP_MS = 120_000;

/**
 * `initial` is what the server rendered (cached up to 60s by Next), so visitors see data
 * immediately even if the backend is asleep. The browser then refreshes every 60s.
 */
export function Dashboard({ initial }: { initial: DashboardData | null }) {
  const [data, setData] = useState(initial);
  const [failed, setFailed] = useState(false);
  // The poller reads the latest ETA without restarting every time data changes.
  const nextSweepAt = useRef<string | null>(null);
  useEffect(() => {
    nextSweepAt.current = data?.summary.next_sweep_at ?? null;
  }, [data]);
  const [attempt, setAttempt] = useState(0); // bumped by "Try again" or a manual sweep to reload now

  useEffect(() => {
    let active = true;
    const refresh = async () => {
      try {
        const next = await loadDashboard({ cache: "no-store" });
        if (active) {
          setData(next);
          setFailed(false);
        }
      } catch {
        // With data on screen we keep showing it; the next tick tries again.
        if (active) setFailed(true);
      }
    };
    if (!initial || attempt > 0) void refresh();
    const id = setInterval(refresh, REFRESH_MS);
    const overdueId = setInterval(() => {
      const due = nextSweepAt.current;
      const late = due ? Date.now() - new Date(due).getTime() : 0;
      if (late > OVERDUE_GRACE_MS && late < OVERDUE_GIVE_UP_MS) void refresh();
    }, OVERDUE_POLL_MS);
    return () => {
      active = false;
      clearInterval(id);
      clearInterval(overdueId);
    };
  }, [initial, attempt]);

  const retry = () => {
    setFailed(false);
    setAttempt((n) => n + 1);
  };

  const openIncidents = data?.incidents.filter((i) => i.resolved_at === null) ?? [];
  const isEmpty = data !== null && data.summary.checks_24h === 0 && data.checks.length === 0;

  return (
    <div className="mx-auto flex max-w-[1280px] flex-col gap-[14px] px-4 py-5 desk:px-7">
      <Header data={data} onSwept={() => setAttempt((n) => n + 1)} />
      {!data && (failed ? <ErrorState onRetry={retry} /> : <DashboardSkeleton />)}
      {data && isEmpty && <EmptyState />}
      {data && !isEmpty && (
        <>
          {openIncidents.length > 0 && <IncidentPanel incidents={openIncidents} />}
          <KpiStrip summary={data.summary} />
          <div className="grid gap-[14px] desk:grid-cols-12">
            <div className="grid gap-[14px] desk:col-span-8 desk:grid-cols-2">
              {data.monitors.map((m) => (
                <LatencyChart key={m.id} name={m.name} series={data.latency[m.id]} asOf={data.fetchedAt} />
              ))}
            </div>
            <div className="desk:col-span-4">
              <CheckLog checks={data.checks} />
            </div>
          </div>
          <Leaderboard monitors={data.monitors} />
          <Achievements items={data.achievements} />
        </>
      )}
      <Footer />
    </div>
  );
}
