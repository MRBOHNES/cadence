import { HpBar } from "./Blocks";
import { HistoryBars } from "./HistoryBars";
import type { Monitor } from "@/lib/api";
import { hostOf, pct } from "@/lib/format";

export function Leaderboard({ monitors }: { monitors: Monitor[] }) {
  const ranked = [...monitors].sort((a, b) => a.rank - b.rank);
  return (
    <section className="panel p-3">
      <div className="mb-2 flex flex-wrap items-baseline justify-between gap-x-4">
        <h2 className="label font-semibold">Leaderboard · ranked by 30-day uptime</h2>
        <p className="text-[12px] text-muted">HP = uptime health, 10 blocks</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-left">
          <caption className="sr-only">Services ranked by 30-day uptime</caption>
          <thead>
            <tr className="label text-muted">
              <th scope="col" className="py-1 pr-3 font-medium">Rank</th>
              <th scope="col" className="py-1 pr-3 font-medium">Service</th>
              <th scope="col" className="py-1 pr-3 font-medium">HP</th>
              <th scope="col" className="hidden py-1 pr-3 font-medium desk:table-cell">24h</th>
              <th scope="col" className="py-1 pr-3 font-medium">30d</th>
              <th scope="col" className="py-1 pr-3 font-medium">30-day history</th>
              <th scope="col" className="py-1 text-right font-medium">Streak</th>
            </tr>
          </thead>
          <tbody>
            {ranked.map((m) => (
              <tr key={m.id} className="border-t border-line">
                <td className="py-2 pr-3">
                  <span className="doto text-[22px]" style={{ color: m.rank === 1 ? "var(--up)" : undefined }}>
                    #{m.rank}
                  </span>
                </td>
                <td className="py-2 pr-3">
                  <p className="font-semibold">{m.name}</p>
                  <p className="font-mono text-[11px] text-muted">{hostOf(m.url)}</p>
                </td>
                <td className="py-2 pr-3"><HpBar hp={m.hp} name={m.name} /></td>
                <td className="hidden py-2 pr-3 font-mono text-[12px] desk:table-cell">{pct(m.uptime_24h ?? null)}</td>
                <td className="py-2 pr-3 font-mono text-[12px]">{pct(m.uptime_30d ?? null)}</td>
                <td className="w-[28%] py-2 pr-3"><HistoryBars name={m.name} history={m.history} /></td>
                <td className="py-2 text-right"><span className="doto text-[18px]">{m.streak_days}d</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
