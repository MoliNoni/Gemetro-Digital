import { describe, expect, test } from "vitest";

import { defaultEntry, entryByHour } from "../src/domain/guidedSelection.js";

function entry(hour, inDomain) {
  return { hour, coverage: { in_domain: inDomain, total: 8 } };
}

describe("defaultEntry (GUIDED_MODE.md §5 implementation decision)", () => {
  test("picks the hour with the highest domain coverage", () => {
    const entries = [entry(11, 0), entry(12, 2), entry(13, 5), entry(14, 1)];
    expect(defaultEntry(entries).hour).toBe(13);
  });

  test("ties go to the earliest hour", () => {
    const entries = [entry(11, 3), entry(12, 5), entry(13, 5)];
    expect(defaultEntry(entries).hour).toBe(12);
  });

  test("null for an empty or missing list", () => {
    expect(defaultEntry([])).toBeNull();
    expect(defaultEntry(null)).toBeNull();
  });
});

describe("entryByHour", () => {
  test("finds the entry for a given hour", () => {
    const entries = [entry(11, 0), entry(12, 2)];
    expect(entryByHour(entries, 12)).toBe(entries[1]);
  });

  test("null when the hour is not in the list", () => {
    expect(entryByHour([entry(11, 0)], 12)).toBeNull();
  });
});
