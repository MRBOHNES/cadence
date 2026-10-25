import { Dashboard } from "@/components/Dashboard";
import { loadDashboard, type Dashboard as DashboardData } from "@/lib/api";

// Incremental static regeneration: the HTML is cached and rebuilt at most once a minute.
export const revalidate = 60;

export default async function Page() {
  let initial: DashboardData | null = null;
  try {
    initial = await loadDashboard({ next: { revalidate: 60 } });
  } catch {
    // Backend asleep or down: render without data; the client fetches on mount.
  }
  return (
    <main>
      <Dashboard initial={initial} />
    </main>
  );
}
