"use client";

import { useState } from "react";
import { triggerSweep } from "@/lib/api";
import { duration } from "@/lib/format";

type Status = { kind: "idle" } | { kind: "running" } | { kind: "done" | "skipped" | "failed"; text: string };

/**
 * The yellow countdown tag doubles as a "sweep now" button. `label` is what the tag shows when
 * idle (the countdown, or DUE). The API allows one sweep every 2 minutes, so repeat clicks are
 * answered with a reason instead of running again.
 */
export function SweepButton({ label, due, onSwept }: { label: string; due: boolean; onSwept: () => void }) {
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const running = status.kind === "running";

  async function sweep() {
    setStatus({ kind: "running" });
    try {
      const result = await triggerSweep();
      if (result.sweep_id === null) {
        setStatus({ kind: "skipped", text: result.skipped ?? "skipped" });
      } else {
        const took = result.duration_ms === null ? "" : ` in ${duration(result.duration_ms)}`;
        setStatus({ kind: "done", text: `sweep #${result.sweep_id} done${took}` });
        onSwept();
      }
    } catch {
      setStatus({ kind: "failed", text: "couldn't reach the API, try again" });
    }
  }

  return (
    <span className="flex items-center gap-2">
      <button
        type="button"
        onClick={sweep}
        disabled={running}
        title="Run a sweep now"
        aria-label={`Run a sweep now. ${due ? "The next scheduled sweep is due." : `Next scheduled sweep in ${label}.`}`}
        // The ::after box widens the tap area to 44px without changing the tag's look.
        className="doto relative cursor-pointer border border-ink bg-hl px-2 py-1 text-[18px] text-[var(--hl-ink)] after:absolute after:-inset-2 after:content-[''] hover:bg-[#e8b520] disabled:cursor-wait"
      >
        {running ? "RUNNING" : label}
      </button>
      <span role="status" aria-live="polite" className="font-mono text-[11px] text-muted">
        {status.kind === "done" || status.kind === "skipped" || status.kind === "failed" ? status.text : ""}
      </span>
    </span>
  );
}
