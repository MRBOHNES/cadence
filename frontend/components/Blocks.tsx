/** 10 HP blocks inside a 1px charcoal frame. Teal, or orange when HP <= 6. */
export function HpBar({ hp, name }: { hp: number; name: string }) {
  const fill = hp <= 6 ? "var(--deg)" : "var(--up)";
  return (
    <div
      className="inline-flex gap-[2px] border border-ink p-[2px]"
      role="img"
      aria-label={`${name} health: ${hp} of 10`}
    >
      {Array.from({ length: 10 }, (_, i) => (
        <span key={i} className="block h-3 w-[7px]" style={{ background: i < hp ? fill : "var(--grid)" }} />
      ))}
    </div>
  );
}

/** 30 blocks, one per streak day (filled in yellow), capped at 30. */
export function StreakBar({ days }: { days: number }) {
  return (
    <div className="flex gap-px" role="img" aria-label={`${Math.min(days, 30)} of 30 days toward the next unlock`}>
      {Array.from({ length: 30 }, (_, i) => (
        <span
          key={i}
          className="block h-2 w-1 border-[0.5px] border-line"
          style={{ background: i < days ? "var(--hl)" : "transparent" }}
        />
      ))}
    </div>
  );
}
