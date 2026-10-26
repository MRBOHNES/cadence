import type { LatencySeries } from "@/lib/api";
import { istTime, ms } from "@/lib/format";

// Plain SVG, no chart library. The viewBox is fixed; CSS scales the whole drawing.
const W = 320;
const H = 140;
const LEFT = 30;
const RIGHT = 314;
const TOP = 8;
const BOTTOM = 118;
const DAY_MS = 24 * 60 * 60 * 1000;

export function LatencyChart({ name, series, asOf }: { name: string; series: LatencySeries; asOf: string }) {
  // The right edge is the moment the data was loaded, so a gap since the last sweep shows as a gap.
  const end = new Date(asOf).getTime();
  const points = series.points
    .map((p) => ({ t: new Date(p.t).getTime(), v: p.latency_ms }))
    .filter((p) => p.t >= end - DAY_MS && p.t <= end);
  const peak = points.reduce((a, b) => (b.v > a.v ? b : a), points[0]);

  // Axis tops out at 600 ms (labels 600/300/0) and grows in 300 ms steps if a spike exceeds it.
  const yMax = Math.max(600, Math.ceil((peak?.v ?? 0) / 300) * 300);
  const x = (t: number) => LEFT + ((t - (end - DAY_MS)) / DAY_MS) * (RIGHT - LEFT);
  const y = (v: number) => BOTTOM - (v / yMax) * (BOTTOM - TOP);

  const line = points.map((p, i) => `${i ? "L" : "M"}${x(p.t).toFixed(1)} ${y(p.v).toFixed(1)}`).join(" ");
  // Close the fill under the last point, not at "now", so a gap since the last sweep stays empty.
  const area = points.length
    ? `${line} L${x(points[points.length - 1].t).toFixed(1)} ${BOTTOM} L${x(points[0].t).toFixed(1)} ${BOTTOM} Z`
    : "";

  const description = points.length
    ? `${name} latency, last 24 hours. Median ${ms(series.p50_ms)} ms, 95th percentile ${ms(series.p95_ms)} ms, ` +
      `peak ${Math.round(peak.v)} ms at ${istTime(peak.t)} IST.`
    : `${name} latency, last 24 hours. No data yet.`;

  return (
    <section className="panel p-3" aria-label={`${name} latency`}>
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="text-[13px] font-semibold">{name}</h2>
        <p className="font-mono text-[11px] text-muted">
          p50 {ms(series.p50_ms)} · p95 {ms(series.p95_ms)} ms
        </p>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="mt-2 block w-full" role="img" aria-label={description}>
        {[0, 0.5, 1].map((f) => {
          const gy = y(yMax * f);
          return (
            <g key={f}>
              <line x1={LEFT} x2={RIGHT} y1={gy} y2={gy} stroke="var(--grid)" strokeWidth={1} />
              <text x={LEFT - 4} y={gy + 3} textAnchor="end" className="fill-muted font-mono" fontSize={10}>
                {Math.round(yMax * f)}
              </text>
            </g>
          );
        })}
        {points.length > 0 && (
          <>
            <path d={area} fill="var(--up)" fillOpacity={0.14} />
            <path d={line} fill="none" stroke="var(--up)" strokeWidth={1.5} strokeLinejoin="round" />
            <circle cx={x(peak.t)} cy={y(peak.v)} r={3.5} fill="var(--deg)" />
          </>
        )}
        <line x1={RIGHT} x2={RIGHT} y1={TOP} y2={BOTTOM} stroke="var(--text)" strokeWidth={1} />
        {points.length === 0 && (
          <text x={(LEFT + RIGHT) / 2} y={(TOP + BOTTOM) / 2} textAnchor="middle" className="fill-muted font-mono" fontSize={10}>
            no data yet
          </text>
        )}
        <text x={LEFT} y={133} className="fill-muted font-mono" fontSize={10}>-24h</text>
        <text x={(LEFT + RIGHT) / 2} y={133} textAnchor="middle" className="fill-muted font-mono" fontSize={10}>-12h</text>
        <text x={RIGHT} y={133} textAnchor="end" className="fill-muted font-mono" fontSize={10}>now</text>
      </svg>
    </section>
  );
}
