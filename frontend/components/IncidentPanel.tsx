import type { Incident } from "@/lib/api";
import { istTime } from "@/lib/format";

function Step({ color, label, at }: { color: string; label: string; at: string | null | undefined }) {
  return (
    <li className="flex items-center gap-2">
      <span className="block size-2 rounded-full" style={{ background: color }} aria-hidden="true" />
      <span className="w-[150px] text-muted">{label}</span>
      <time dateTime={at ?? undefined}>{at ? `${istTime(at)} IST` : "--"}</time>
    </li>
  );
}

/** Shown above the KPI strip while any incident is unresolved. */
export function IncidentPanel({ incidents }: { incidents: Incident[] }) {
  return (
    <section aria-labelledby="incident-heading" className="border border-down bg-panel p-3">
      <h2 id="incident-heading" className="label font-semibold text-down">
        Open incident{incidents.length > 1 ? "s" : ""}
      </h2>
      {incidents.map((i) => (
        <div key={i.id} className="mt-2">
          <p className="font-semibold">
            {i.monitor_name} <span className="font-mono text-[12px] font-normal text-muted">· {i.cause}</span>
          </p>
          <ol className="mt-1.5 space-y-1 font-mono text-[12px]">
            <Step color="var(--up)" label="last OK check" at={i.last_ok_at} />
            <Step color="var(--deg)" label="first failure" at={i.started_at} />
            <Step color="var(--down)" label="incident opened" at={i.opened_at} />
          </ol>
        </div>
      ))}
    </section>
  );
}
