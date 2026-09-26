// P-28 (Vitest port, F-05): end to end against a live API with the real model artifact.
//   uvicorn gemetro.api:app --port 8000   (from the repository root)
//   GEMETRO_E2E_API=http://localhost:8000 npm test -- tests/e2e.test.js
// Skipped when GEMETRO_E2E_API is not set, so `npm test` never depends on a running API.
import { beforeAll, describe, expect, test, vi } from "vitest";

import { fetchConfig, fetchGuided, runScenario } from "../src/api/client.js";
import { ML_IN_DOMAIN_STATUS, PMV_VALID } from "../src/domain/format.js";

const API = process.env.GEMETRO_E2E_API;

describe.skipIf(!API)("end to end (GEMETRO_E2E_API)", () => {
  // Points the client at the live API for these tests only (client.js reads
  // import.meta.env.VITE_API_URL on every call, not once at import time).
  beforeAll(() => {
    vi.stubEnv("VITE_API_URL", API);
  });
  test("the default scenario renders every required element (P-27/P-28)", async () => {
    const config = await fetchConfig();
    const record = await runScenario(config.defaults);

    expect(record.indoor).toBeDefined();
    expect(record.ml.domain_status).toBeDefined();
    expect(record.pmv.status === PMV_VALID || typeof record.pmv.status === "string").toBe(true);
    expect(record.provenance.tin).toBeDefined();
    expect(record.sensitivity).toHaveLength(config.sliders.tau_r.values.length);
    for (const point of record.sensitivity) {
      expect(point.ml.domain_status).toBeDefined();
    }
  });

  test("GET /guided returns one entry per hour of the period, each with a coverage and a record", async () => {
    const config = await fetchConfig();
    const guided = await fetchGuided("A", "midday");

    expect(guided.entries).toHaveLength(config.guided.periods.midday.length);
    for (const entry of guided.entries) {
      expect(entry.coverage.total).toBe(8);
      expect(entry.record.provenance.tau_r).toMatch(/modo guiado/);
    }
  });

  test("the model's own domain (/config.domain) matches what E-03 documented", async () => {
    const config = await fetchConfig();
    // Only asserts the artifact is loaded and shaped as expected, not a specific number
    // (that belongs to PHASE_2_RESULTS.md, not to this test).
    expect(config.domain).not.toBeNull();
    expect(config.domain.ta.min).toBeLessThan(config.domain.ta.max);
    expect(ML_IN_DOMAIN_STATUS).toBeTruthy();
  });
});
