"use client";

import { useSyncExternalStore } from "react";

function subscribe(onTick: () => void) {
  const id = setInterval(onTick, 1000);
  return () => clearInterval(id);
}

// Whole seconds, so repeated reads between ticks return the same value.
const snapshot = () => Math.floor(Date.now() / 1000) * 1000;

/**
 * Current time in ms, ticking every second. Null on the server and during hydration so the
 * first client render matches the server HTML. Runs regardless of prefers-reduced-motion:
 * it is information, not animation.
 */
export function useNow(): number | null {
  return useSyncExternalStore(subscribe, snapshot, () => null);
}
