// Approved scenario presets (design doc, 2026-09-25): presets set only the hour.
// φ, τr, vel, clo and posture keep the closed /config defaults (CA-10).

export const PRESETS = [
  { id: "madrugada", label: "Madrugada", hour: 5 },
  { id: "manana", label: "Mañana", hour: 7 },
  { id: "mediodia", label: "Mediodía", hour: 12 },
  { id: "tarde", label: "Tarde", hour: 16 },
  { id: "noche", label: "Noche", hour: 20 },
];

export const DEFAULT_PRESET_ID = "tarde";

export function findPresetByHour(hour) {
  return PRESETS.find((preset) => preset.hour === hour) ?? null;
}

export function findPresetById(id) {
  return PRESETS.find((preset) => preset.id === id) ?? null;
}

const NON_HOUR_KEYS = ["line", "phi_peak", "tau_r", "vel", "clo", "posture"];

// True when the current scenario differs from "selected preset + defaults": advanced (ΔT)
// mode, an hour that matches no preset, or any non-hour value that differs from /config
// defaults.
export function isCustomConfiguration(scenario, defaults) {
  if (scenario.advanced) return true;
  if (findPresetByHour(scenario.hour) === null) return true;
  return NON_HOUR_KEYS.some((key) => scenario[key] !== defaults[key]);
}

// Builds the POST /scenario request body from the user-facing scenario state: `advanced`
// is a frontend-only flag (the API infers advanced mode from delta_t being non-null), and
// delta_t is only sent when advanced mode is on (ScenarioRequest.delta_t defaults to None).
export function toScenarioParams(scenario) {
  const { advanced, delta_t, ...rest } = scenario;
  return { ...rest, delta_t: advanced ? delta_t : null };
}
