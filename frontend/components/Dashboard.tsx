"use client";

import { useCallback, useEffect, useState } from "react";
import { Achievements } from "./Achievements";
import { CheckLog } from "./CheckLog";
import { Footer } from "./Footer";
import { Header } from "./Header";
import { KpiStrip } from "./KpiStrip";
import { LatencyChart } from "./LatencyChart";
import { Leaderboard } from "./Leaderboard";
import { loadDashboard, type Dashboard as DashboardData } from "@/lib/api";

const REFRESH_MS = 60_000;

/**
 * `initial` is what the server rendered (cached up to 60s by Next), so visitors see data
 * immediately even if the backend is asleep. The browser then refreshes every 60s.
 */
export function Dashboard({ initial }: { initial: DashboardData | null }) {
  const [data, setData] = useState(initial);

  const refresh = useCallback(async () => {
    try {
      setData(await loadDashboard({ cache: "no-store" }));
    } catch {
      // Keep showing the last good data; the next tick tries again.
    }
  }, []);

  useEffect(() => {
    if (!initial) refresh();
    const id = setInterval(refresh, REFRESH_MS);
    return () => clearInterval(id);
  }, [initial, refresh]);

  return (
    <div className="mx-auto flex max-w-[1280px] flex-col gap-[14px] px-7 py-5">
      <Header data={data} />
      {data && (
        <>
          <KpiStrip summary={data.summary} />
          <div className="grid gap-[14px] desk:grid-cols-12">
            <div className="grid gap-[14px] desk:col-span-8 desk:grid-cols-2">
              {data.monitors.map((m) => (
                <LatencyChart key={m.id} name={m.name} series={data.latency[m.id]} />
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
