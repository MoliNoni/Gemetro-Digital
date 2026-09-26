import { describe, expect, test } from "vitest";

import {
  DEFAULT_PRESET_ID,
  PRESETS,
  findPresetByHour,
  findPresetById,
  isCustomConfiguration,
  toScenarioParams,
} from "../src/domain/presets.js";

const DEFAULTS = { line: "A", hour: 16, phi_peak: 0.75, tau_r: 60, vel: 0.3, clo: 0.5, posture: "seated" };

test("presets only set the hour (5, 7, 12, 16, 20)", () => {
  expect(PRESETS.map((p) => p.hour)).toEqual([5, 7, 12, 16, 20]);
});

// DEFAULTS.hour here is a fixture, not a live /config read; this only checks internal
// consistency between the preset list and this fixture. E2E (F-05) checks it against the
// real API's closed default (CA-10: line A, 16 h).
test("default preset (Tarde) hour is consistent with the fixture's default hour", () => {
  const defaultPreset = findPresetById(DEFAULT_PRESET_ID);
  expect(defaultPreset.hour).toBe(DEFAULTS.hour);
});

describe("isCustomConfiguration", () => {
  test("preset hour + defaults is not custom", () => {
    expect(isCustomConfiguration({ ...DEFAULTS, advanced: false }, DEFAULTS)).toBe(false);
  });

  test("an hour outside the presets is custom", () => {
    expect(isCustomConfiguration({ ...DEFAULTS, hour: 9, advanced: false }, DEFAULTS)).toBe(true);
  });

  test("any non-hour value differing from defaults is custom", () => {
    expect(isCustomConfiguration({ ...DEFAULTS, tau_r: 90, advanced: false }, DEFAULTS)).toBe(true);
    expect(isCustomConfiguration({ ...DEFAULTS, line: "B", advanced: false }, DEFAULTS)).toBe(true);
  });

  test("advanced (ΔT) mode is always custom", () => {
    expect(isCustomConfiguration({ ...DEFAULTS, advanced: true }, DEFAULTS)).toBe(true);
  });

  test("findPresetByHour returns null for a non-preset hour", () => {
    expect(findPresetByHour(9)).toBeNull();
    expect(findPresetByHour(5).label).toBe("Madrugada");
  });
});

describe("toScenarioParams", () => {
  test("omits delta_t (sends null) when not in advanced mode", () => {
    const params = toScenarioParams({ ...DEFAULTS, advanced: false, delta_t: 4 });
    expect(params).toEqual({ ...DEFAULTS, delta_t: null });
  });

  test("sends delta_t when in advanced mode", () => {
    const params = toScenarioParams({ ...DEFAULTS, advanced: true, delta_t: 4 });
    expect(params).toEqual({ ...DEFAULTS, delta_t: 4 });
  });
});
