// P-27 (unit level): formatting, rounding and the one-line explanations show every state
// as received from the API, with no confidence/accuracy figure. Component-level "same
// block" and "per τr point" assertions are ported in F-02's result-card tests, once those
// components exist.
import { describe, expect, test } from "vitest";

import {
  ATTRIBUTION,
  DISCLAIMER,
  classLabel,
  formatPercent,
  formatPmvValue,
  formatTemperature,
  mlStatusKind,
  pmvStatusKind,
} from "../src/domain/format.js";
import {
  mlDomainExplanation,
  pmvOutOfRangeExplanation,
  simulatorStatusExplanation,
} from "../src/domain/explanations.js";
import { CONFIG, EXTRAPOLATION, IN_DOMAIN, ML_IN, ML_OUT, PMV_OUT, RECORD, SIM_OUT } from "./fixtures.js";

describe("presentation rounding", () => {
  test("temperatures round to 0.5 °C", () => {
    expect(formatTemperature(31.45)).toBe("31.5 °C");
    expect(formatTemperature(27.1)).toBe("27.0 °C");
  });

  test("humidity rounds to 1 %", () => {
    expect(formatPercent(0.453)).toBe("45 %");
  });

  test("PMV rounds to 0.1", () => {
    expect(formatPmvValue(0.31)).toBe("0.3");
  });
});

describe("status kind (extrapolation is informational, not an error)", () => {
  test("in-domain ML status is ok", () => {
    expect(mlStatusKind(IN_DOMAIN)).toBe("ok");
  });

  test("extrapolation status is warn, never an error kind", () => {
    expect(mlStatusKind(EXTRAPOLATION)).toBe("warn");
  });

  test("valid PMV is ok, out of range is warn", () => {
    expect(pmvStatusKind("valid")).toBe("ok");
    expect(pmvStatusKind(PMV_OUT)).toBe("warn");
  });
});

describe("class labels", () => {
  test("maps API classes to Spanish labels", () => {
    expect(classLabel("cool")).toBe("fresco");
    expect(classLabel("neutral")).toBe("neutral");
    expect(classLabel("warm")).toBe("cálido");
  });
});

describe("explanations are built only from API fields", () => {
  test("ML out-of-domain explanation names the field and its value", () => {
    const text = mlDomainExplanation(RECORD);
    expect(text).toContain("humedad interior");
    expect(text).toContain(formatPercent(RECORD.indoor.rh_in));
    expect(text).toContain("temperatura interior");
    expect(text).toContain(formatTemperature(RECORD.indoor.tin_c));
    expect(text).toContain("Nanjing");
  });

  test("no ML explanation when in domain", () => {
    const inDomainRecord = { ...RECORD, ml: ML_IN };
    expect(mlDomainExplanation(inDomainRecord)).toBe("");
  });

  test("PMV out-of-range explanation cites ISO 7730 without a bound number", () => {
    const text = pmvOutOfRangeExplanation(RECORD);
    expect(text).toContain("ISO 7730");
    expect(text).toMatch(/[Tt]emperatura interior/);
    expect(text).not.toMatch(/\d+\s*°C|\d+\s*%|[-+]?\d\.\d\s*(a|-)\s*[-+]?\d/);
  });

  test("simulator status explanation uses the API's Tin value, no hardcoded bound", () => {
    const record = { ...RECORD, indoor: { ...RECORD.indoor, tin_c: 55, simulator_status: SIM_OUT } };
    const text = simulatorStatusExplanation(record);
    expect(text).toContain("55.0 °C");
    expect(text).not.toMatch(/50\s*°C/);
  });
});

test("no confidence, probability or accuracy figure appears anywhere in shared texts", () => {
  const text = (DISCLAIMER + ATTRIBUTION + mlDomainExplanation(RECORD) +
    pmvOutOfRangeExplanation(RECORD)).toLowerCase();
  for (const word of ["confianza", "probabilidad", "precisión", "exactitud", "f1", "acierto"]) {
    expect(text.includes(word)).toBe(false);
  }
});

test("ML class and PMV out-of-range fixtures keep the original status strings verbatim", () => {
  expect(ML_OUT.domain_status).toBe(EXTRAPOLATION);
  expect(RECORD.pmv.status).toBe(PMV_OUT);
});

// G-02: with a bounds config passed, the explanation also states the violated bound, taken
// only from that config (never a literal in explanations.js). Omitting the bounds config
// (the tests above) must keep reading exactly as before.
describe("explanations with bounds (G-02, /config.domain and /config.pmv_ranges)", () => {
  test("ML explanation states the training-domain bound when `domain` is passed", () => {
    const text = mlDomainExplanation(RECORD, CONFIG.domain);
    expect(text).toContain("rango de entrenamiento");
    // RECORD.ml.out_of_domain is ["ta", "rh"]; both bounds should appear.
    expect(text).toMatch(/2[01].*°C.*3[01].*°C/s);
    expect(text).toMatch(/52 %.*89 %/s);
  });

  test("PMV explanation states the valid range when `pmvRanges` is passed", () => {
    const text = pmvOutOfRangeExplanation(RECORD, CONFIG.pmv_ranges);
    expect(text).toContain("rango válido");
    expect(text).toMatch(/10.*°C.*30.*°C/s);
  });

  test("no bound is stated when the bounds config is omitted (backward compatible)", () => {
    expect(mlDomainExplanation(RECORD)).not.toContain("rango de entrenamiento");
    expect(pmvOutOfRangeExplanation(RECORD)).not.toContain("rango válido");
  });
});
