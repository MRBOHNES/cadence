import type { Monitor } from "@/lib/api";

type Day = Monitor["history"][number];

const STYLE: Record<Day, { height: number; fill: string }> = {
  up: { height: 20, fill: "var(--up)" },
  degraded: { height: 10, fill: "var(--deg)" }, // half height: not colour alone
  down: { height: 20, fill: "var(--down)" },
  "no-data": { height: 2, fill: "var(--none)" },
};

const BAR = 4;
const GAP = 2;

/** 30 daily bars, oldest on the left. */
export function HistoryBars({ name, history }: { name: string; history: Day[] }) {
  const count = (d: Day) => history.filter((h) => h === d).length;
  const label =
    `${name}, last 30 days: ${count("up")} up, ${count("degraded")} degraded, ` +
    `${count("down")} down, ${count("no-data")} without data.`;
  return (
    <svg
      viewBox={`0 0 ${history.length * (BAR + GAP) - GAP} 20`}
      className="block h-5 w-full min-w-[150px]"
      preserveAspectRatio="none"
      role="img"
      aria-label={label}
    >
      {history.map((day, i) => {
        const s = STYLE[day];
        return (
          <g key={i}>
            <rect x={i * (BAR + GAP)} y={20 - s.height} width={BAR} height={s.height} fill={s.fill} />
            {day === "down" && <rect x={i * (BAR + GAP)} y={0} width={BAR} height={3} fill="var(--text)" />}
          </g>
        );
      })}
    </svg>
  );
}
