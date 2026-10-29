import { StreakBar } from "./Blocks";
import { Marked, type Tone } from "./Marker";
import type { Summary } from "@/lib/api";
import { SLOW_MS, ms, pct, signed } from "@/lib/format";


function Cell({
  label,
  value,
  marker = false,
  children,
}: {
  label: string;
  value: string;
  marker?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-panel p-3.5">
      <div className="mb-2 h-[3px] w-6" style={{ background: marker ? "var(--hl)" : "transparent" }} aria-hidden="true" />
      <p className="label text-muted">{label}</p>
      <p className="doto mt-1.5 text-[34px]">{value}</p>
      <div className="mt-2 font-mono text-[11px]">{children}</div>
    </div>
  );
}

function Change({ tone, children }: { tone: Tone; children: React.ReactNode }) {
  return (
    <p>
      <Marked tone={tone}>{children}</Marked>
    </p>
  );
}

export function KpiStrip({ summary }: { summary: Summary }) {
  const slowestMs = summary.slowest_p95_ms ?? null;
  const down = summary.services_total - summary.services_up;
  const change = summary.uptime_change ?? null;
  return (
    <section aria-label="Key figures" className="panel grid grid-cols-2 gap-px bg-line desk:grid-cols-6">
      <Cell label="Uptime 30d" value={pct(summary.uptime_30d ?? null)} marker>
        {change === null ? (
          <Change tone="muted">no prior data</Change>
        ) : (
          <Change tone={change >= 0 ? "good" : "bad"}>{signed(change, 2)} pts vs prev 30d</Change>
        )}
      </Cell>
      <Cell label="Streak" value={`${summary.streak_days}d`} marker>
        <StreakBar days={summary.streak_days} />
        <p className="mt-1.5 text-muted">next unlock at 30d · best {summary.best_streak_days}d</p>
      </Cell>
      <Cell label="Services up" value={`${summary.services_up}/${summary.services_total}`}>
        <Change tone={down ? "bad" : "good"}>{down ? `${down} down` : "all healthy"}</Change>
      </Cell>
      {/* Latency is per service: pooling GitHub with a cold-starting API would describe neither. */}
      <Cell label="Slowest p95 ms" value={ms(slowestMs)}>
        {summary.slowest_service ? (
          <Change tone={slowestMs !== null && slowestMs > SLOW_MS ? "warn" : "good"}>{summary.slowest_service}</Change>
        ) : (
          <Change tone="muted">no data yet</Change>
        )}
      </Cell>
      <Cell label="Slow checks 24h" value={String(summary.slow_checks_24h)}>
        <Change tone={summary.slow_checks_24h ? "warn" : "muted"}>over {SLOW_MS} ms, still up</Change>
      </Cell>
      <Cell label="Checks 24h" value={String(summary.checks_24h)}>
        <Change tone={summary.failed_24h ? "bad" : "muted"}>{summary.failed_24h} failed</Change>
      </Cell>
    </section>
  );
}
