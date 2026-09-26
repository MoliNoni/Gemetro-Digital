// P-27 at component level: every τr sweep point's ML and PMV status is visible without
// interaction — as a compact table (visual redesign §11), not only encoded in a hover-only
// chart tooltip.
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";

import SensitivityChart from "../src/components/SensitivityChart.jsx";
import { RECORD } from "./fixtures.js";

afterEach(cleanup);

describe("SensitivityChart", () => {
  test("lists every non-excluded point of the sweep with its own status, without needing a hover", () => {
    render(<SensitivityChart record={RECORD} pragueReferenceS={24} />);

    const table = screen.getByRole("table");
    const rows = table.querySelectorAll("tbody tr");
    // Feedback round 2 (point 6): the 240 s point is excluded from display, so only the
    // fixture's other two points (20 s, 60 s) remain.
    expect(rows.length).toBe(RECORD.sensitivity.length - 1);

    // First point (τr 20 s) is in-domain/valid; second (60 s) is not.
    expect(rows[0].textContent).toMatch(/20 s/);
    expect(rows[1].textContent).toMatch(/60 s/);
  });

  test("excludes the 240 s point from the chart and table (display-only, direction 2026-09-25)", () => {
    render(<SensitivityChart record={RECORD} pragueReferenceS={24} />);
    expect(screen.queryByText("240 s")).not.toBeInTheDocument();
  });

  test("marks the currently selected τr", () => {
    render(<SensitivityChart record={RECORD} pragueReferenceS={24} />);
    // RECORD.scenario.tau_r === 60 and mode is "normal".
    const selected = document.querySelector("tr.is-selected");
    expect(selected.textContent).toMatch(/60 s/);
  });

  test("marks an out-of-domain/out-of-range row amber, distinct from the selected row", () => {
    render(<SensitivityChart record={RECORD} pragueReferenceS={24} />);
    // Second point (60 s) is ML/PMV out of domain and out of range (fixtures.js ML_OUT/PMV_NO).
    const rows = [...screen.getByRole("table").querySelectorAll("tbody tr")];
    const outOfDomainRow = rows.find((row) => row.textContent.includes("60 s"));
    expect(outOfDomainRow.className).toMatch(/is-out-of-domain/);
  });

  test("no confidence, probability or accuracy figure is shown", () => {
    render(<SensitivityChart record={RECORD} pragueReferenceS={24} />);
    const text = document.body.textContent.toLowerCase();
    for (const word of ["confianza", "probabilidad", "precisión", "exactitud", "f1", "acierto"]) {
      expect(text.includes(word)).toBe(false);
    }
  });
});
