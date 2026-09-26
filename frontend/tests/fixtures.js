// Example API responses shared by the Vitest suite (hand written; they only exercise
// presentation, ported from the previous tests/render.test.js).

export const IN_DOMAIN = "Dentro del dominio de entrenamiento";
export const EXTRAPOLATION = "Extrapolación / fuera del dominio de entrenamiento";
export const PMV_OUT = "Fuera de rango para PMV";
export const SIM_OUT = "fuera de validez del simulador";

export function point(tau, tin, simStatus, ml, pmv) {
  return {
    tau_r: tau,
    tin_c: tin,
    rh_in: 0.5,
    delta_t: tin - 25,
    rh_limited: false,
    simulator_status: simStatus,
    ml,
    pmv,
  };
}

export const ML_IN = { comfort_class: "neutral", domain_status: IN_DOMAIN, out_of_domain: [] };
export const ML_OUT = { comfort_class: "warm", domain_status: EXTRAPOLATION, out_of_domain: ["ta", "rh"] };
export const PMV_OK = { status: "valid", value: 0.31, comfort_class: "neutral", out_of_range: [] };
export const PMV_NO = { status: PMV_OUT, value: null, comfort_class: null, out_of_range: ["ta"] };

// Mirrors gemetro.scenario.scenario_config() (src/gemetro/scenario.py): SLIDERS, DEFAULTS,
// LINES, POSTURES and PRAGUE_TAU_REFERENCE_S, as returned by GET /config.
export const CONFIG = {
  lines: ["A", "B"],
  postures: ["seated", "standing"],
  day_type: "weekday",
  sliders: {
    hour: { min: 4, max: 22, step: 1, default: 16 },
    phi_peak: { min: 0.5, max: 1.0, step: 0.05, default: 0.75 },
    tau_r: { values: [20, 30, 45, 60, 90, 120, 180, 240], default: 60 },
    vel: { min: 0.1, max: 1.5, step: 0.05, default: 0.3 },
    clo: { min: 0.2, max: 1.0, step: 0.05, default: 0.5 },
    delta_t: { min: 0.0, max: 18.0, step: 0.5, default: null },
  },
  defaults: { line: "A", hour: 16, phi_peak: 0.75, tau_r: 60, vel: 0.3, clo: 0.5, posture: "seated" },
  prague_tau_reference_s: 24,
  fixed_parameters: {},
  provenance: {},
  domain: {
    ta: { min: 21.07, max: 31.63 },
    rh: { min: 52.05, max: 89.47 },
    vel: { min: 0.08, max: 1.72 },
    clo: { min: 0.17, max: 1.06 },
    postures: ["seated", "standing"],
  },
  pmv_ranges: {
    ta: { min: 10.0, max: 30.0 },
    tr: { min: 10.0, max: 40.0 },
    vel: { min: 0.0, max: 1.0 },
    met: { min: 0.8, max: 4.0 },
    clo: { min: 0.0, max: 2.0 },
    pa: { min: 0.0, max: 2700.0 },
    pmv: { min: -2.0, max: 2.0 },
  },
  guided: {
    periods: {
      morning: [4, 5, 6, 7, 8, 9, 10],
      midday: [11, 12, 13, 14],
      afternoon: [15, 16, 17, 18],
      night: [19, 20, 21, 22],
    },
    // Default posture is "seated" for both modes (direction 2026-09-26).
    fixed: { phi_peak: 0.75, vel: 0.3, clo: 0.5, posture: "seated" },
    default_tau_r: 60,
    selection_rule: "in_domain_closest_to_default_tau_r",
  },
};

export const RECORD = {
  scenario: {
    line: "A", day_type: "weekday", hour: 16, phi_peak: 0.75, tau_r: 60, vel: 0.3,
    clo: 0.5, posture: "standing", mode: "normal", delta_t: null,
  },
  outdoor: { tout_c: 25.01, rh_out: 0.584 },
  occupancy: { n: 225, phi: 0.75, c_wagon: 300 },
  met: 1.2,
  indoor: { tin_c: 31.45, rh_in: 0.453, delta_t: 6.44, rh_limited: false, simulator_status: null },
  ml: ML_OUT,
  pmv: PMV_NO,
  provenance: {
    tout: "Dato real, agregado", rh_out: "Dato real, agregado", n: "Derivado / simulado",
    tin: "Simulado", rh_in: "Simulado", ml_class: "Predicho", pmv: "Asignación normativa",
  },
  sensitivity: [
    point(20, 27.1, null, ML_IN, PMV_OK),
    point(60, 31.45, null, ML_OUT, PMV_NO),
    point(240, 55.0, SIM_OUT, ML_OUT, PMV_NO),
  ],
};

// One GET /guided entry (GUIDED_MODE.md §3.2): in-domain selection at 16 h.
export const GUIDED_ENTRY_IN_DOMAIN = {
  hour: 16,
  coverage: { in_domain: 3, total: 8 },
  selected_tau_r: 20,
  selection: "in_domain",
  record: {
    ...RECORD,
    scenario: { ...RECORD.scenario, hour: 16, tau_r: 20, posture: "seated" },
    ml: ML_IN,
    pmv: PMV_OK,
    provenance: { ...RECORD.provenance, tau_r: "Supuesto de escenario (seleccionado por el modo guiado)" },
  },
};

// No in-domain τr for this hour (e.g. midday, GUIDED_MODE.md §2): fallback to the default
// τr, marked "no_in_domain_fallback".
export const GUIDED_ENTRY_FALLBACK = {
  hour: 12,
  coverage: { in_domain: 0, total: 8 },
  selected_tau_r: 60,
  selection: "no_in_domain_fallback",
  record: {
    ...RECORD,
    scenario: { ...RECORD.scenario, hour: 12, tau_r: 60, posture: "seated" },
    ml: ML_OUT,
    pmv: PMV_NO,
    provenance: { ...RECORD.provenance, tau_r: "Supuesto de escenario (seleccionado por el modo guiado)" },
  },
};

export function guidedResponse(line, period, entries) {
  return {
    line,
    period,
    hours: entries.map((entry) => entry.hour),
    fixed: CONFIG.guided.fixed,
    selection_rule: CONFIG.guided.selection_rule,
    entries,
  };
}
