export type Tone = "good" | "bad" | "warn" | "muted";

const SQUARE: Record<Tone, string> = {
  good: "var(--up)",
  bad: "var(--down)",
  warn: "var(--deg)",
  muted: "var(--none)",
};

/**
 * Small status text. Teal (4.1:1) and orange (3.7:1) miss the 4.5:1 contrast bar on the panel
 * colour at this size, so the words stay charcoal and the meaning is carried by a coloured
 * square beside them. Red passes (4.9:1) on the panel and is used for failures as designed;
 * pass `ink` where it sits on the tinted failure row (4.4:1).
 */
export function Marked({ tone, ink = false, children }: { tone: Tone; ink?: boolean; children: React.ReactNode }) {
  return (
    <span className={tone === "bad" && !ink ? "text-down" : tone === "muted" ? "text-muted" : "text-ink"}>
      {tone !== "muted" && (
        <span className="mr-1.5 inline-block size-2" style={{ background: SQUARE[tone] }} aria-hidden="true" />
      )}
      {children}
    </span>
  );
}
