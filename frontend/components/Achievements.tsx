import { PixelIcon, type IconName } from "./PixelIcon";
import type { Achievement } from "@/lib/api";

const ICONS: Record<string, IconName> = {
  "99_9_club": "trophy",
  sub_100ms: "bolt",
  iron_wall: "shield",
  on_fire: "flame",
  perfect_month: "heart",
};

function unlockedOn(iso: string): string {
  return new Date(iso)
    .toLocaleDateString("en-GB", { timeZone: "Asia/Kolkata", day: "2-digit", month: "short" })
    .toUpperCase();
}

export function Achievements({ items }: { items: Achievement[] }) {
  const unlocked = items.filter((a) => a.unlocked).length;
  return (
    <section aria-labelledby="achievements-heading">
      <div className="mb-2 flex items-baseline justify-between">
        <h2 id="achievements-heading" className="label font-semibold">Achievements</h2>
        <p className="font-mono text-[12px] text-muted">{unlocked} / {items.length} unlocked</p>
      </div>
      <ul className="grid grid-cols-2 gap-[14px] desk:grid-cols-5">
        {items.map((a) => {
          const icon = ICONS[a.id] ?? "trophy";
          const gold = icon === "trophy";
          return (
            <li
              key={a.id}
              className={`border border-line p-3 ${a.unlocked ? "bg-panel" : "bg-transparent"}`}
            >
              <PixelIcon name={icon} color={a.unlocked ? (gold ? "var(--gold)" : "var(--up)") : "var(--none)"} />
              <h3 className={`doto mt-2 text-[15px] ${a.unlocked ? "" : "text-muted"}`}>{a.title}</h3>
              <p className="mt-1.5 text-[12px]">{a.description}</p>
              <p className={`mt-2 font-mono text-[11px] ${a.unlocked ? "text-up" : "text-muted"}`}>
                {a.unlocked && a.unlocked_at ? `UNLOCKED · ${unlockedOn(a.unlocked_at)}` : a.progress}
              </p>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
