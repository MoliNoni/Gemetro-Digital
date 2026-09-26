import { describe, expect, test } from "vitest";

import { compareMlPmv } from "../src/domain/comparison.js";
import { ML_IN, PMV_NO, PMV_OK, RECORD } from "./fixtures.js";

describe("compareMlPmv", () => {
  test("agree is true when both in-domain/valid results give the same class", () => {
    const record = { ...RECORD, ml: { ...ML_IN, comfort_class: "neutral" }, pmv: PMV_OK };
    const result = compareMlPmv(record);
    expect(result.agree).toBe(true);
    expect(result.caveat).toBe(false);
  });

  test("agree is false when both resolve but disagree", () => {
    const record = { ...RECORD, ml: { ...ML_IN, comfort_class: "warm" }, pmv: PMV_OK };
    const result = compareMlPmv(record);
    expect(result.agree).toBe(false);
    expect(result.caveat).toBe(false);
  });

  test("agree is null (not a normal-validity comparison) when PMV is out of range", () => {
    const record = { ...RECORD, ml: ML_IN, pmv: PMV_NO };
    const result = compareMlPmv(record);
    expect(result.agree).toBeNull();
    expect(result.caveat).toBe(true);
  });

  test("caveat is true when the ML is extrapolating, even if PMV resolves", () => {
    const result = compareMlPmv(RECORD); // RECORD.ml is ML_OUT (extrapolation)
    expect(result.caveat).toBe(true);
  });
});
