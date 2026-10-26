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
  // When this data was loaded. Charts end here, so server HTML and hydration draw the same "now".
  fetchedAt: string;
};

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init);
  if (!response.ok) throw new Error(`${path} responded ${response.status}`);
  return response.json() as Promise<T>;
}

export type SweepResult = components["schemas"]["SweepResult"];

/** The page's "sweep now" button. The API rate-limits it to one sweep every 2 minutes. */
export async function triggerSweep(): Promise<SweepResult> {
  const response = await fetch(`${API_URL}/sweep`, { method: "POST", cache: "no-store" });
  if (!response.ok) throw new Error(`/sweep responded ${response.status}`);
  return response.json() as Promise<SweepResult>;
}

/**
 * Loads everything the page shows. `init` carries Next's caching options on the server
 * (`{ next: { revalidate: 60 } }`) and is omitted in the browser.
 */
export async function loadDashboard(init?: RequestInit): Promise<Dashboard> {
  const fetchedAt = new Date().toISOString();
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
    fetchedAt,
  };
}
