"use client";

import type { Dashboard } from "@/lib/api";
import { countdown, istTime } from "@/lib/format";
import { useNow } from "@/lib/useNow";

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
          <span className="font-mono text-[12px] text-muted">sweep #{data.summary.latest_sweep}</span>
        )}
        <span className="flex items-center gap-2 font-mono text-[12px] text-muted">
          next
          <span
            role="timer"
            aria-label="Time until next sweep"
            className="doto border border-ink bg-hl px-2 py-1 text-[18px] text-[var(--hl-ink)]"
          >
            {now ? countdown(data?.summary.next_sweep_at ?? null, now) : "--:--"}
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
