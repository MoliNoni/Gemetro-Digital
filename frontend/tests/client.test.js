// G-01/G-02: fetchGuided builds the right query string, and a non-ok response's status is
// attached to the thrown Error so callers can distinguish 503 (model not loaded) from any
// other failure without re-parsing the message.
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { fetchConfig, fetchGuided, runScenario } from "../src/api/client.js";

function jsonResponse(body, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  });
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("fetchGuided", () => {
  test("requests GET /guided with the line and period as query parameters", async () => {
    fetch.mockReturnValue(jsonResponse({ entries: [] }));
    await fetchGuided("A", "midday");

    const [url] = fetch.mock.calls[0];
    expect(url).toMatch(/\/guided\?/);
    expect(url).toContain("line=A");
    expect(url).toContain("period=midday");
  });
});

describe("error.status", () => {
  test("a 503 response's error carries status 503", async () => {
    fetch.mockReturnValue(jsonResponse({ detail: "model not loaded" }, 503));
    await expect(fetchConfig()).rejects.toMatchObject({ status: 503, message: "model not loaded" });
  });

  test("a 422 response's error carries status 422", async () => {
    fetch.mockReturnValue(jsonResponse({ detail: "line must be one of ('A', 'B')" }, 422));
    await expect(runScenario({})).rejects.toMatchObject({ status: 422 });
  });
});
