"""Guided mode (GUIDED_MODE.md §3): one representative scenario per hour of a period.

Per hour only the line and the hour vary; φ_peak, vel, clo and posture stay at the Phase 1
defaults. τr is selected from the existing eight-point sensitivity sweep of run_scenario:
the in-domain point (ML inside the training domain and simulator inside its validity) closest
to the default τr, ties going to the shorter τr. With no such point the default τr is used and
the entry is marked as a fallback. The scenario service itself is not changed.
"""

from __future__ import annotations

from gemetro.comfort_model import STATUS_IN_DOMAIN, ComfortModel
from gemetro.scenario import (
    DEFAULTS,
    LINES,
    SCENARIO_ASSUMPTION,
    Scenario,
    ScenarioError,
    run_scenario,
)

PERIODS = {
    "morning": (4, 10),
    "midday": (11, 14),
    "afternoon": (15, 18),
    "night": (19, 22),
}
FIXED = {name: DEFAULTS[name] for name in ("phi_peak", "vel", "clo", "posture")}
SELECTION_RULE = "in_domain_closest_to_default_tau_r"
SELECTED_IN_DOMAIN = "in_domain"
SELECTED_FALLBACK = "no_in_domain_fallback"
GUIDED_TAU_PROVENANCE = f"{SCENARIO_ASSUMPTION} (seleccionado por el modo guiado)"


def period_hours(period: str) -> list[int]:
    if period not in PERIODS:
        raise ScenarioError(f"period must be one of {tuple(PERIODS)}")
    first, last = PERIODS[period]
    return list(range(first, last + 1))


def _in_domain(point: dict) -> bool:
    return point["ml"]["domain_status"] == STATUS_IN_DOMAIN and point["simulator_status"] is None


def select_tau_r(sweep: list[dict]) -> tuple[int, str, int]:
    """(τr, selection, in-domain point count) for one hour's sensitivity sweep."""
    candidates = [point["tau_r"] for point in sweep if _in_domain(point)]
    if not candidates:
        return DEFAULTS["tau_r"], SELECTED_FALLBACK, 0
    tau = min(candidates, key=lambda value: (abs(value - DEFAULTS["tau_r"]), value))
    return tau, SELECTED_IN_DOMAIN, len(candidates)


def _entry(line: str, hour: int, model: ComfortModel) -> dict:
    probe = run_scenario(Scenario(line=line, hour=hour, **FIXED), model)
    tau, selection, in_domain = select_tau_r(probe["sensitivity"])
    record = probe
    if tau != probe["scenario"]["tau_r"]:
        record = run_scenario(Scenario(line=line, hour=hour, tau_r=tau, **FIXED), model)
    record["provenance"]["tau_r"] = GUIDED_TAU_PROVENANCE
    return {
        "hour": hour,
        "coverage": {"in_domain": in_domain, "total": len(probe["sensitivity"])},
        "selected_tau_r": tau,
        "selection": selection,
        "record": record,
    }


def run_guided(line: str, period: str, model: ComfortModel) -> dict:
    """Representative scenario for every hour of one line and period."""
    if line not in LINES:
        raise ScenarioError(f"line must be one of {LINES}")
    hours = period_hours(period)
    return {
        "line": line,
        "period": period,
        "hours": hours,
        "fixed": dict(FIXED),
        "selection_rule": SELECTION_RULE,
        "entries": [_entry(line, hour, model) for hour in hours],
    }


def guided_config() -> dict:
    """Periods, fixed parameters and selection rule for the frontend (I-17)."""
    return {
        "periods": {name: period_hours(name) for name in PERIODS},
        "fixed": dict(FIXED),
        "default_tau_r": DEFAULTS["tau_r"],
        "selection_rule": SELECTION_RULE,
    }
