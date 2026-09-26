import { describe, expect, test } from "vitest";

import {
  MAX_WAGON_FIGURES,
  PASSENGERS_PER_FIGURE,
  figureCount,
  isFigureCountCapped,
  periodForHour,
} from "../src/domain/wagon.js";

describe("figureCount", () => {
  test("rounds N to the nearest figure at the drawing scale (1 figure ≈ 10 passengers)", () => {
    expect(figureCount(225)).toBe(23); // 22.5 rounds to 23 (Math.round)
    expect(figureCount(220)).toBe(22);
    expect(figureCount(4)).toBe(0); // rounds down to 0
    expect(figureCount(5)).toBe(1); // rounds up to 1 (0.5 tie)
  });

  test("draws no figures for missing, zero, negative or non-finite N", () => {
    expect(figureCount(null)).toBe(0);
    expect(figureCount(undefined)).toBe(0);
    expect(figureCount(0)).toBe(0);
    expect(figureCount(-5)).toBe(0);
    expect(figureCount(NaN)).toBe(0);
    expect(figureCount(Infinity)).toBe(0);
  });

  test("caps the figure count to what the drawing can fit", () => {
    expect(figureCount(MAX_WAGON_FIGURES * PASSENGERS_PER_FIGURE)).toBe(MAX_WAGON_FIGURES);
    expect(figureCount(1000)).toBe(MAX_WAGON_FIGURES);
  });
});

describe("isFigureCountCapped", () => {
  test("false when N fits (including missing N)", () => {
    expect(isFigureCountCapped(225)).toBe(false);
    expect(isFigureCountCapped(MAX_WAGON_FIGURES * PASSENGERS_PER_FIGURE)).toBe(false);
    expect(isFigureCountCapped(null)).toBe(false);
    expect(isFigureCountCapped(undefined)).toBe(false);
    expect(isFigureCountCapped(NaN)).toBe(false);
  });

  test("true when the raw figure count exceeds what the drawing shows", () => {
    expect(isFigureCountCapped(MAX_WAGON_FIGURES * PASSENGERS_PER_FIGURE + PASSENGERS_PER_FIGURE)).toBe(true);
    expect(isFigureCountCapped(1000)).toBe(true);
  });
});

describe("periodForHour", () => {
  // Feedback round 2 (direction 2026-09-25, point 10): boundaries are aligned with the
  // guided-mode backend buckets (src/gemetro/guided.py PERIODS: morning 4-10, midday 11-14,
  // afternoon 15-18, night 19-22), not the previous preset-hour midpoints.
  test("maps every guided-mode representative hour to its aligned period", () => {
    expect(periodForHour(7)).toBe("manana"); // guided "morning" 4-10
    expect(periodForHour(12)).toBe("mediodia"); // guided "midday" 11-14
    expect(periodForHour(16)).toBe("tarde"); // guided "afternoon" 15-18
    expect(periodForHour(20)).toBe("noche"); // guided "night" 19-22
    expect(periodForHour(2)).toBe("madrugada");
  });

  test("boundaries (midpoints between consecutive guided-bucket edges) switch period", () => {
    expect(periodForHour(3.9)).toBe("madrugada");
    expect(periodForHour(4)).toBe("manana");

    expect(periodForHour(10.4)).toBe("manana");
    expect(periodForHour(10.5)).toBe("mediodia");

    expect(periodForHour(14.4)).toBe("mediodia");
    expect(periodForHour(14.5)).toBe("tarde");

    expect(periodForHour(18.4)).toBe("tarde");
    expect(periodForHour(18.5)).toBe("noche");
  });

  test("wraps around midnight: late night and just-past-midnight are both noche", () => {
    expect(periodForHour(23)).toBe("noche");
    expect(periodForHour(0)).toBe("noche");
    expect(periodForHour(0.4)).toBe("noche");
    expect(periodForHour(0.5)).toBe("madrugada");
  });
});
