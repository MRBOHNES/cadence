import type { RecentCheck } from "@/lib/api";
import { Marked } from "./Marker";
import { SLOW_MS, istTime } from "@/lib/format";

export function CheckLog({ checks }: { checks: RecentCheck[] }) {
  return (
    <section className="panel p-3">
      <h2 className="label mb-2 font-semibold">Recent checks</h2>
      <table className="w-full font-mono text-[12px]">
        <caption className="sr-only">Most recent checks, newest first. Times are IST.</caption>
        <thead>
          <tr className="label text-left text-muted">
            <th scope="col" className="py-1 pr-2 font-medium">time</th>
            <th scope="col" className="py-1 pr-2 font-medium">svc</th>
            <th scope="col" className="py-1 pr-2 font-medium">code</th>
            <th scope="col" className="py-1 text-right font-medium">ms</th>
          </tr>
        </thead>
        <tbody>
          {checks.map((c) => {
            const slow = c.ok && c.latency_ms !== null && c.latency_ms > SLOW_MS;
            return (
              <tr key={c.id} style={c.ok ? undefined : { background: "var(--down-tint)" }}>
                <td className="py-1 pr-2">{istTime(c.checked_at)}</td>
                <td className="py-1 pr-2">{c.short_code}</td>
                <td className="py-1 pr-2">
                  {c.ok ? c.status_code : (
                    <span className="font-medium">
                      <Marked tone="bad" ink>{c.status_code ?? (c.error === "timeout" ? "timeout" : "error")}</Marked>
                    </span>
                  )}
                </td>
                <td className="py-1 text-right">
                  {slow ? <Marked tone="warn">{c.latency_ms}</Marked> : (c.latency_ms ?? "--")}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
