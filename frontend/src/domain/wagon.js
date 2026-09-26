// Pure helpers for MetroCarVisualization (F-03). No model value is computed here: figure
// count is a presentation scale ("1 figure ≈ 10 passengers") over the N the API already
// returned (record.occupancy.n, the same field ResultCards reads), and the time-of-day
// period is derived only from the scenario hour, with boundaries consistent with the
// approved presets (5, 7, 12, 16, 20 — design doc, 2026-09-25).

export const PASSENGERS_PER_FIGURE = 10;

// 6 columns x 5 rows in the drawing grid (MetroCarVisualization.jsx): the most the wagon
// can show without the figures overlapping or shrinking past legibility.
export const MAX_WAGON_FIGURES = 30;

// Number of passenger figures to draw for a given N (API-returned occupancy.n), capped to
// what the drawing can fit. Missing/invalid N draws no figures rather than throwing.
export function figureCount(n, maxFigures = MAX_WAGON_FIGURES) {
  if (n == null || !Number.isFinite(n) || n <= 0) return 0;
  const raw = Math.round(n / PASSENGERS_PER_FIGURE);
  return Math.min(raw, maxFigures);
}

// True when the raw (uncapped) figure count for N exceeds what the drawing shows, so the
// caller can say so in the caption instead of silently under-representing occupancy.
export function isFigureCountCapped(n, maxFigures = MAX_WAGON_FIGURES) {
  if (n == null || !Number.isFinite(n)) return false;
  return Math.round(n / PASSENGERS_PER_FIGURE) > maxFigures;
}

// Period boundaries (feedback round 2, direction 2026-09-25, point 10): aligned with the
// guided-mode backend buckets (src/gemetro/guided.py PERIODS: morning 4-10, midday 11-14,
// afternoon 15-18, night 19-22) instead of the previous preset-hour midpoints, so the
// wagon's ambience is coherent with the periods guided mode actually offers. Boundaries are
// the midpoints between consecutive bucket edges (treated circularly over the 24 h day):
// madrugada [0.5, 4), mañana [4, 10.5), mediodía [10.5, 14.5), tarde [14.5, 18.5),
// noche [18.5, 24) ∪ [0, 0.5).
export const PERIOD_LABELS = {
  madrugada: "madrugada",
  manana: "mañana",
  mediodia: "mediodía",
  tarde: "tarde",
  noche: "noche",
};

export function periodForHour(hour) {
  const h = ((Number(hour) % 24) + 24) % 24;
  if (h >= 18.5 || h < 0.5) return "noche";
  if (h >= 14.5) return "tarde";
  if (h >= 10.5) return "mediodia";
  if (h >= 4) return "manana";
  return "madrugada";
}
