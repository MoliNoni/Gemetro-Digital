// API client: GET /config, POST /scenario and GET /guided, as is (no new field invented
// here). The frontend computes no model value; every scientific number comes from these
// responses.

// Read on every call (not frozen into a module-level constant) so tests can point the
// client at a live API (e.g. via vi.stubEnv) without needing a fresh module instance.
function apiBase() {
  return (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
}

async function getJson(path, options) {
  const response = await fetch(`${apiBase()}${path}`, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    // `status` lets callers distinguish "model not loaded" (503, both /scenario and
    // /guided) from any other error without re-parsing the message.
    const error = new Error(body.detail || `HTTP ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return body;
}

export function fetchConfig(options) {
  return getJson("/config", options);
}

export function runScenario(scenarioParams, options) {
  return getJson("/scenario", {
    ...options,
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(scenarioParams),
  });
}

// GUIDED_MODE.md §5: one representative scenario per hour of a line/period.
export function fetchGuided(line, period, options) {
  const params = new URLSearchParams({ line, period });
  return getJson(`/guided?${params}`, options);
}

function hourRange(sliders) {
  const hours = [];
  for (let hour = sliders.hour.min; hour <= sliders.hour.max; hour += sliders.hour.step) {
    hours.push(hour);
  }
  return hours;
}

// One record per hour of the day (config.sliders.hour.min..max), all sharing the current
// non-hour parameters. Runs the /scenario calls in parallel; no new endpoint is introduced.
export async function runDayProfile(nonHourParams, config, options) {
  const hours = hourRange(config.sliders);
  const records = await Promise.all(
    hours.map((hour) => runScenario({ ...nonHourParams, hour }, options)),
  );
  return hours.map((hour, index) => ({ hour, record: records[index] }));
}
