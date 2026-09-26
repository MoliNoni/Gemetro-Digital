"""I-16: scenario service — one Medellín scenario in, one complete record out.

Chain (one way, no feedback): scenario -> N -> simulator -> Tin, RH_in -> ML and PMV
(PROJECT_DECISION.md §2). The record follows PHASE_1_ARCHITECTURE.md §3: indoor conditions,
ML class with domain status, PMV value/class or out-of-range status, provenance of every
variable, and the τr sensitivity sweep in the same response (L-03: normal mode, the eight
discrete τr values, each point with its own ML and PMV status).

Values are returned unrounded; rounding is presentation (PHASE_2_IMPLEMENTATION.md §3).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from gemetro.comfort_model import ComfortModel, ComfortPrediction
from gemetro.data.climate import CLIMATE_ARTIFACT
from gemetro.occupancy import C_WAGON, load_ratio, occupancy_fraction
from gemetro.pmv import MET_BY_POSTURE, PmvResult, pmv_baseline
from gemetro.simulator import (
    G_KG_S,
    P_HPA,
    Q_SENSIBLE_W,
    VOLUME_M3,
    SimulationResult,
    simulate,
    simulate_advanced,
)

# Scenario configuration, PHASE_1_ARCHITECTURE.md §9.2.
TAU_VALUES = (20, 30, 45, 60, 90, 120, 180, 240)
PRAGUE_TAU_REFERENCE_S = 24  # external reference mark, not a limit
SLIDERS = {
    "hour": {"min": 4, "max": 22, "step": 1, "default": 16},
    "phi_peak": {"min": 0.5, "max": 1.0, "step": 0.05, "default": 0.75},
    "tau_r": {"values": list(TAU_VALUES), "default": 60},
    "vel": {"min": 0.1, "max": 1.5, "step": 0.05, "default": 0.3},
    "clo": {"min": 0.2, "max": 1.0, "step": 0.05, "default": 0.5},
    "delta_t": {"min": 0.0, "max": 18.0, "step": 0.5, "default": None},
}
LINES = ("A", "B")
POSTURES = ("seated", "standing")
# Default posture is "seated" (scenario assumption changed by direction, 2026-09-26, for both
# guided and simulation modes; Phase 1/2 documented runs used "standing").
DEFAULTS = {"line": "A", "hour": 16, "phi_peak": 0.75, "tau_r": 60, "vel": 0.3, "clo": 0.5,
            "posture": "seated"}

# Provenance categories (AGENTS.md §4; PHASE_1_ARCHITECTURE.md §9.2).
REAL = "Dato real"
REAL_AGGREGATED = "Dato real, agregado"
REFERENCE = "Referencia"
DERIVED_SIMULATED = "Derivado / simulado"
SCENARIO_ASSUMPTION = "Supuesto de escenario"
USER_ASSUMPTION = "Supuesto del usuario"
SIMULATED = "Simulado"
PREDICTED = "Predicho"
NORMATIVE = "Asignación normativa"
ASSUMPTION = "Supuesto"

PROVENANCE = {
    "line": REAL,
    "day_type": REAL_AGGREGATED,
    "hour": REAL,
    "tout": REAL_AGGREGATED,
    "rh_out": REAL_AGGREGATED,
    "phi_peak": SCENARIO_ASSUMPTION,
    "n": DERIVED_SIMULATED,
    "c_wagon": REFERENCE,
    "tau_r": SCENARIO_ASSUMPTION,
    "vel": SCENARIO_ASSUMPTION,
    "clo": SCENARIO_ASSUMPTION,
    "posture": SCENARIO_ASSUMPTION,
    "tin": SIMULATED,
    "rh_in": SIMULATED,
    "ml_class": PREDICTED,
    "pmv": NORMATIVE,
    "met": NORMATIVE,
}
FIXED_PARAMETERS = {
    "p_hpa": {"value": P_HPA, "provenance": "Dato real (constante)"},
    "volume_m3": {"value": VOLUME_M3, "provenance": ASSUMPTION},
    "q_s_w": {"value": Q_SENSIBLE_W, "provenance": REFERENCE},
    "g_g_per_h": {"value": round(G_KG_S * 1000 * 3600), "provenance": REFERENCE},
    "c_wagon": {"value": C_WAGON, "provenance": REFERENCE},
}


class ScenarioError(ValueError):
    """The scenario is outside the configured sliders."""


@dataclass(frozen=True)
class Scenario:
    line: str = DEFAULTS["line"]
    hour: int = DEFAULTS["hour"]
    phi_peak: float = DEFAULTS["phi_peak"]
    tau_r: int = DEFAULTS["tau_r"]
    vel: float = DEFAULTS["vel"]
    clo: float = DEFAULTS["clo"]
    posture: str = DEFAULTS["posture"]
    delta_t: float | None = None  # advanced mode when set

    def validate(self) -> None:
        if self.line not in LINES:
            raise ScenarioError(f"line must be one of {LINES}")
        if self.posture not in POSTURES:
            raise ScenarioError(f"posture must be one of {POSTURES}")
        if self.tau_r not in TAU_VALUES:
            raise ScenarioError(f"tau_r must be one of {TAU_VALUES}")
        for name in ("hour", "phi_peak", "vel", "clo"):
            _check_slider(name, getattr(self, name))
        if self.delta_t is not None:
            _check_slider("delta_t", self.delta_t)


def _check_slider(name: str, value: float) -> None:
    spec = SLIDERS[name]
    if not isinstance(value, int | float) or math.isnan(value):
        raise ScenarioError(f"{name} must be a number")
    if not spec["min"] - 1e-9 <= value <= spec["max"] + 1e-9:
        raise ScenarioError(f"{name} must be within [{spec['min']}, {spec['max']}]")
    steps = (value - spec["min"]) / spec["step"]
    if abs(steps - round(steps)) > 1e-6:
        raise ScenarioError(f"{name} must be a multiple of {spec['step']} from {spec['min']}")


@lru_cache(maxsize=1)
def _climate() -> dict[int, tuple[float, float]]:
    table = pd.read_csv(CLIMATE_ARTIFACT)
    return {int(r.hour): (float(r.tout_c), float(r.rh_out)) for r in table.itertuples()}


def outdoor_conditions(hour: int) -> tuple[float, float]:
    """(Tout °C, RH_out fraction): 2025 hourly median, IDEAM Olaya Herrera."""
    return _climate()[hour]


def _ml(prediction: ComfortPrediction) -> dict:
    return {
        "comfort_class": prediction.comfort_class,
        "domain_status": prediction.domain_status,
        "out_of_domain": list(prediction.out_of_domain),
    }


def _pmv(result: PmvResult) -> dict:
    return {
        "status": result.status,
        "value": result.pmv,
        "comfort_class": result.pmv_class,
        "out_of_range": list(result.reasons),
    }


def _comfort(model: ComfortModel, sim: SimulationResult, scenario: Scenario) -> tuple[dict, dict]:
    rh_percent = sim.rh_in * 100.0
    ml = model.predict(sim.tin, rh_percent, scenario.vel, scenario.clo, scenario.posture)
    pmv = pmv_baseline(sim.tin, rh_percent, scenario.vel, scenario.clo, scenario.posture)
    return _ml(ml), _pmv(pmv)


def _indoor(sim: SimulationResult) -> dict:
    return {
        "tin_c": sim.tin,
        "rh_in": sim.rh_in,
        "delta_t": sim.delta_t,
        "rh_limited": sim.rh_limited,
        "simulator_status": sim.status,
    }


def run_scenario(scenario: Scenario, model: ComfortModel) -> dict:
    """Complete record for one scenario (PHASE_1_ARCHITECTURE.md §3)."""
    scenario.validate()
    tout, rh_out = outdoor_conditions(scenario.hour)
    phi = occupancy_fraction(load_ratio(scenario.line, scenario.hour), scenario.phi_peak)
    n = phi * C_WAGON
    advanced = scenario.delta_t is not None

    if advanced:
        sim = simulate_advanced(tout, rh_out, n, scenario.delta_t)
    else:
        sim = simulate(tout, rh_out, n, scenario.tau_r)
    ml, pmv = _comfort(model, sim, scenario)
    indoor = _indoor(sim)
    if advanced:
        indoor["tau_r_implied"] = sim.tau_r

    sweep = []
    for tau in TAU_VALUES:
        point = simulate(tout, rh_out, n, tau)
        point_ml, point_pmv = _comfort(model, point, scenario)
        sweep.append({"tau_r": tau, **_indoor(point), "ml": point_ml, "pmv": point_pmv})

    provenance = dict(PROVENANCE)
    if advanced:
        provenance["delta_t"] = USER_ASSUMPTION
        provenance["tau_r_implied"] = DERIVED_SIMULATED
    return {
        "scenario": {
            "line": scenario.line,
            "day_type": "weekday",
            "hour": scenario.hour,
            "phi_peak": scenario.phi_peak,
            "tau_r": scenario.tau_r,
            "vel": scenario.vel,
            "clo": scenario.clo,
            "posture": scenario.posture,
            "mode": "advanced" if advanced else "normal",
            "delta_t": scenario.delta_t,
        },
        "outdoor": {"tout_c": tout, "rh_out": rh_out},
        "occupancy": {"n": n, "phi": phi, "c_wagon": C_WAGON},
        "met": MET_BY_POSTURE[scenario.posture],
        "indoor": indoor,
        "ml": ml,
        "pmv": pmv,
        "provenance": provenance,
        "sensitivity": sweep,
    }


def scenario_config() -> dict:
    """Slider ranges, defaults, fixed parameters and provenance for the frontend (I-17)."""
    return {
        "lines": list(LINES),
        "postures": list(POSTURES),
        "day_type": "weekday",
        "sliders": SLIDERS,
        "defaults": DEFAULTS,
        "prague_tau_reference_s": PRAGUE_TAU_REFERENCE_S,
        "fixed_parameters": FIXED_PARAMETERS,
        "provenance": PROVENANCE,
    }
