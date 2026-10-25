// 7x7 pixel art; "1" = filled square. Drawn as SVG rects with crisp edges.
const GRIDS = {
  trophy: ["1111111", "1111111", "0111110", "0011100", "0001000", "0011100", "0111110"],
  bolt: ["0001100", "0011000", "0110000", "1111110", "0001100", "0011000", "0110000"],
  shield: ["1111111", "1111111", "1111111", "1111111", "0111110", "0011100", "0001000"],
  flame: ["0001000", "0011000", "0011100", "0111110", "1111111", "1110111", "0111110"],
  heart: ["0110110", "1111111", "1111111", "0111110", "0011100", "0001000", "0000000"],
} as const;

export type IconName = keyof typeof GRIDS;

export function PixelIcon({ name, color, size = 40 }: { name: IconName; color: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 7 7" shapeRendering="crispEdges" aria-hidden="true">
      {GRIDS[name].flatMap((row, y) =>
        [...row].map((cell, x) => (cell === "1" ? <rect key={`${x}-${y}`} x={x} y={y} width={1} height={1} fill={color} /> : null)),
      )}
    </svg>
  );
}
