"use client";

import { useEffect, useState } from "react";

/**
 * Current time in ms, ticking every second. Null until mounted so server and first client
 * render match (no hydration mismatch). Runs regardless of prefers-reduced-motion: it is
 * information, not animation.
 */
export function useNow(): number | null {
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    setNow(Date.now());
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}
