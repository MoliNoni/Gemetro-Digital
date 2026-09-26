// F-03 component tests: accessible name (line + period + approx passengers), figure count
// rendered from the fixture N, the "not to scale" label, and graceful handling of a
// missing/loading N.
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";

import MetroCarVisualization from "../src/components/MetroCarVisualization.jsx";
import { MAX_WAGON_FIGURES } from "../src/domain/wagon.js";
import { RECORD } from "./fixtures.js";

afterEach(cleanup);

function renderedFigureCount(container) {
  return [...container.querySelectorAll(".mc-figure")].filter(
    (node) => node.style.opacity !== "0",
  ).length;
}

describe("MetroCarVisualization", () => {
  test("accessible name mentions the line, the period and the approximate N", () => {
    render(<MetroCarVisualization line="A" hour={7} n={225} />);

    const img = screen.getByRole("img");
    expect(img.getAttribute("aria-label")).toMatch(/línea A/i);
    expect(img.getAttribute("aria-label")).toMatch(/mañana/i);
    expect(img.getAttribute("aria-label")).toMatch(/225/);
  });

  test("renders one figure per 10 passengers from the fixture's N (occupancy.n)", () => {
    const { container } = render(
      <MetroCarVisualization line={RECORD.scenario.line} hour={RECORD.scenario.hour} n={RECORD.occupancy.n} />,
    );

    // RECORD.occupancy.n === 225 -> round(225 / 10) === 23
    expect(renderedFigureCount(container)).toBe(23);
  });

  // Feedback round 3 (direction 2026-09-26): the visible scale tooltip was removed; the
  // accessible name still states the drawing is illustrative and not to scale.
  test('the accessible name says the drawing is illustrative and "no a escala"', () => {
    render(<MetroCarVisualization line="A" hour={16} n={225} />);
    expect(screen.getByRole("img").getAttribute("aria-label")).toMatch(/no a escala/i);
  });

  test("draws no figures and does not crash when N is missing (loading state)", () => {
    const { container } = render(<MetroCarVisualization line="A" hour={16} n={undefined} />);

    expect(renderedFigureCount(container)).toBe(0);
    expect(screen.getByRole("img").getAttribute("aria-label")).toMatch(/no disponible/i);
  });

  test("caps the drawn figures when N overflows the drawing", () => {
    const { container } = render(<MetroCarVisualization line="A" hour={16} n={2000} />);

    expect(renderedFigureCount(container)).toBe(MAX_WAGON_FIGURES);
  });

  test("each period maps to a distinct time-of-day ambience", () => {
    // hour=2 falls in "madrugada" under the guided-period-aligned boundaries
    // (domain/wagon.js, feedback round 2, point 10) — 5 h is now "mañana".
    const { container, rerender } = render(<MetroCarVisualization line="A" hour={2} n={0} />);
    expect(container.querySelector(".metro-car-visualization").dataset.period).toBe("madrugada");

    rerender(<MetroCarVisualization line="A" hour={20} n={0} />);
    expect(container.querySelector(".metro-car-visualization").dataset.period).toBe("noche");
  });
});
