const IST = "Asia/Kolkata";

export const SLOW_MS = 500;

/** 14:05:09 in IST. Explicit timeZone keeps server and browser output identical. */
export function istTime(iso: string | number | Date): string {
  return new Date(iso).toLocaleTimeString("en-GB", { timeZone: IST, hour12: false });
}

export function hostOf(url: string): string {
  return new URL(url).host;
}

/** "+0.02" / "-12" / "0": explicit sign so direction is readable without colour. */
export function signed(value: number, digits = 0): string {
  const rounded = Number(value.toFixed(digits));
  if (rounded === 0) return "0";
  return `${rounded > 0 ? "+" : "-"}${Math.abs(rounded).toFixed(digits)}`;
}

export function pct(value: number | null, digits = 2): string {
  return value === null ? "--" : `${value.toFixed(digits)}%`;
}

export function ms(value: number | null): string {
  return value === null ? "--" : `${Math.round(value)}`;
}

/** mm:ss until `target`, never negative. */
export function countdown(target: string | null, now: number): string {
  if (!target) return "--:--";
  const seconds = Math.max(0, Math.round((new Date(target).getTime() - now) / 1000));
  const m = String(Math.floor(seconds / 60)).padStart(2, "0");
  const s = String(seconds % 60).padStart(2, "0");
  return `${m}:${s}`;
}

/** "45s ago" / "12m ago" / "3h ago" / "2d ago". */
export function ago(iso: string, now: number): string {
  const seconds = Math.max(0, Math.round((now - new Date(iso).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}
