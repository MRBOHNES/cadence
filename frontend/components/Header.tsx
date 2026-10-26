"use client";

import type { Dashboard } from "@/lib/api";
import { ago, countdown, istTime } from "@/lib/format";
import { useNow } from "@/lib/useNow";

// The cron is best-effort, so the countdown is a prediction. Past it, say "due" rather than
// sitting at 00:00, and show the last sweep's age once it is clearly stale.
const DUE_GRACE_MS = 5_000;
const STALE_AFTER_MS = 10 * 60_000;

function overallState(monitors: Dashboard["monitors"]) {
  const down = monitors.filter((m) => m.state === "down").length;
  const slow = monitors.filter((m) => m.state === "slow").length;
  if (down) return { label: `${down} DOWN`, color: "var(--down)" };
  if (slow) return { label: `${slow} SLOW`, color: "var(--deg)" };
  if (monitors.some((m) => m.state === "unknown")) return { label: "NO DATA", color: "var(--muted)" };
  return { label: "ALL UP", color: "var(--up)" };
}

export function Header({ data }: { data: Dashboard | null }) {
  const now = useNow();
  const state = data ? overallState(data.monitors) : null;
  const nextAt = data?.summary.next_sweep_at ?? null;
  const lastAt = data?.summary.latest_sweep_at ?? null;
  const due = now !== null && nextAt !== null && now > new Date(nextAt).getTime() + DUE_GRACE_MS;
  const stale = now !== null && lastAt !== null && now - new Date(lastAt).getTime() > STALE_AFTER_MS;
  return (
    <header className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 border-b border-line pb-3">
      <div className="flex items-baseline gap-3">
        <h1 className="doto text-[26px] tracking-wide">CADENCE</h1>
        <span className="text-muted">status / overview</span>
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        {state && (
          <span role="status" className="flex items-center gap-2 font-mono text-[12px] font-medium">
            <span className="block size-2.5" style={{ background: state.color }} aria-hidden="true" />
            {state.label}
          </span>
        )}
        {data?.summary.latest_sweep != null && (
          <span className="font-mono text-[12px] text-muted">
            sweep #{data.summary.latest_sweep}
            {stale && lastAt && now !== null && ` · ${ago(lastAt, now)}`}
          </span>
        )}
        <span className="flex items-center gap-2 font-mono text-[12px] text-muted">
          next
          <span
            role="timer"
            aria-label={due ? "Next sweep is due" : "Time until next sweep"}
            className="doto border border-ink bg-hl px-2 py-1 text-[18px] text-[var(--hl-ink)]"
          >
            {now === null ? "--:--" : due ? "DUE" : countdown(nextAt, now)}
          </span>
        </span>
        <span className="flex items-baseline gap-2">
          <span className="doto text-[18px]" suppressHydrationWarning>
            {now ? istTime(now) : "--:--:--"}
          </span>
          <span className="font-mono text-[12px] text-muted">IST</span>
        </span>
      </div>
    </header>
  );
}
