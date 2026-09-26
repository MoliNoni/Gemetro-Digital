import {
  PERIOD_LABELS,
  figureCount,
  periodForHour,
} from "../domain/wagon.js";

// Passenger layout (feedback round 2, point 11): three depth rows of ten slots
// (3 x 10 = MAX_WAGON_FIGURES). Rows overlap vertically — back-row bodies sit behind
// front-row heads — so a full wagon reads as a packed, overlapping crowd, while a light
// load stays sparse. Back rows are smaller and fainter, front rows larger and more solid.
const DEPTH_ROWS = [
  { headY: 88, scale: 0.78, opacity: 0.28, offset: 17 }, // back
  { headY: 100, scale: 0.9, opacity: 0.48, offset: 8 }, // middle
  { headY: 114, scale: 1.0, opacity: 0.74, offset: 0 }, // front
];
const SLOTS_PER_ROW = 10;
// Deterministic horizontal jitter (no Math.random, so layout is stable across renders and
// tests): breaks the perfectly even spacing without any randomness.
const JITTER = [0, 4, -3, 2, -4, 3, -2, 5, -1, 1];

// Fill order: spread the first passengers across the whole car (front row, even slots
// first), then fill the gaps and the rows behind, so occupancy grows as "more crowded",
// not as "one corner fills up first".
const FILL_PASSES = [
  [2, 0], [1, 1], [0, 0], [2, 1], [1, 0], [0, 1],
]; // [row, slot parity]
const FILL_RANK = new Map();
FILL_PASSES.forEach(([row, parity]) => {
  for (let col = parity; col < SLOTS_PER_ROW; col += 2) FILL_RANK.set(`${row}-${col}`, FILL_RANK.size);
});

// Drawn back-to-front so front silhouettes overlap the ones behind them.
const FIGURE_POSITIONS = DEPTH_ROWS.flatMap((row, r) =>
  Array.from({ length: SLOTS_PER_ROW }, (_, col) => ({
    key: `${r}-${col}`,
    rank: FILL_RANK.get(`${r}-${col}`),
    x: 36 + col * 34 + row.offset + JITTER[(col + r * 3) % JITTER.length],
    y: row.headY,
    scale: row.scale,
    opacity: row.opacity,
  })),
);

const WINDOW_COUNT = 6;

// F-03: the wagon is the visual protagonist of the page — a schematic 2D SVG, not a data
// chart. Occupancy figures come only from the API-returned N (occupancy.n, the same field
// ResultCards reads); there is no control to set N. The time-of-day ambience comes only
// from the currently selected hour (scenario state), so it updates immediately, before the
// debounced API result for N arrives. Everything here is decorative/illustrative: no door
// or seat count is claimed anywhere.
export default function MetroCarVisualization({ line, hour, n }) {
  const period = periodForHour(hour);
  const periodLabel = PERIOD_LABELS[period];
  const hasN = n != null && Number.isFinite(n);
  const count = figureCount(n);

  const ariaLabel = hasN
    ? `Esquema del vagón, línea ${line}, ${periodLabel}, aproximadamente ${Math.round(n)} ` +
      "pasajeros. Ilustrativo, no a escala."
    : `Esquema del vagón, línea ${line}, ${periodLabel}, ocupación aún no disponible. ` +
      "Ilustrativo, no a escala.";

  return (
    <div className="metro-car-visualization" data-period={period}>
      <svg
        className="metro-car"
        viewBox="0 0 400 210"
        role="img"
        aria-label={ariaLabel}
      >
        <title>{ariaLabel}</title>
        <rect className="mc-sky" x="0" y="0" width="400" height="210" />
        {/* A solid badge behind the line label (visual QA fix): the label must stay legible
            over all four sky ambients (from a near-black "noche" to a light "mediodía"
            blue), and a text-color-only choice cannot guarantee that on its own. */}
        <rect className="mc-line-badge" x="10" y="8" width="72" height="20" rx="0" />
        <text className="mc-line-label" x="16" y="22">Línea {line}</text>
        <g className="mc-wagon">
          <rect className="mc-body" x="10" y="34" width="380" height="148" rx="8" />
          <rect className="mc-interior-light" x="18" y="42" width="364" height="132" rx="4" />
          {Array.from({ length: WINDOW_COUNT }, (_, i) => (
            <rect
              key={`window-${i}`}
              className="mc-window"
              x={30 + i * 58}
              y="50"
              width="40"
              height="32"
              rx="1"
            />
          ))}
          <clipPath id="mc-interior-clip">
            <rect x="18" y="42" width="364" height="132" rx="4" />
          </clipPath>
          <g className="mc-passengers" aria-hidden="true" clipPath="url(#mc-interior-clip)">
            {FIGURE_POSITIONS.map((pos) => (
              <g
                key={`figure-${pos.key}`}
                className="mc-figure"
                style={{ opacity: pos.rank < count ? pos.opacity : 0 }}
                transform={`translate(${pos.x}, ${pos.y}) scale(${pos.scale})`}
              >
                {/* Upper-body human silhouette: filled head + shoulders/torso, no stroke —
                    reads as a person at this scale and stays clean when overlapped. */}
                <circle className="mc-figure-head" cx="0" cy="0" r="7" />
                <path
                  className="mc-figure-body"
                  d="M -12 22 C -12 12 -7 9 0 9 C 7 9 12 12 12 22 L 12 70 L -12 70 Z"
                />
              </g>
            ))}
          </g>
        </g>
      </svg>
    </div>
  );
}
