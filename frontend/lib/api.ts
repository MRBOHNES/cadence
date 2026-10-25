import type { components } from "./api-types";

export type Summary = components["schemas"]["Summary"];
export type Monitor = components["schemas"]["MonitorOut"];
export type LatencySeries = components["schemas"]["LatencySeries"];
export type RecentCheck = components["schemas"]["RecentCheck"];
export type Incident = components["schemas"]["IncidentOut"];
export type Achievement = components["schemas"]["AchievementOut"];

export type Dashboard = {
  summary: Summary;
  monitors: Monitor[];
  latency: Record<number, LatencySeries>; // keyed by monitor id
  checks: RecentCheck[];
  incidents: Incident[];
  achievements: Achievement[];
};

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init);
  if (!response.ok) throw new Error(`${path} responded ${response.status}`);
  return response.json() as Promise<T>;
}

/**
 * Loads everything the page shows. `init` carries Next's caching options on the server
 * (`{ next: { revalidate: 60 } }`) and is omitted in the browser.
 */
export async function loadDashboard(init?: RequestInit): Promise<Dashboard> {
  const [summary, monitors, checks, incidents, achievements] = await Promise.all([
    get<Summary>("/summary", init),
    get<Monitor[]>("/monitors", init),
    get<RecentCheck[]>("/checks/recent?limit=50", init),
    get<Incident[]>("/incidents?limit=20", init),
    get<Achievement[]>("/achievements", init),
  ]);
  const series = await Promise.all(
    monitors.map((m) => get<LatencySeries>(`/monitors/${m.id}/latency?range=24h`, init)),
  );
  return {
    summary,
    monitors,
    checks,
    incidents,
    achievements,
    latency: Object.fromEntries(series.map((s) => [s.monitor_id, s])),
  };
}
