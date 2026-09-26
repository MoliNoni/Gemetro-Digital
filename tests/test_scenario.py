"""P-22, P-23 (service part) and scenario validation (I-16)."""

import json

import pytest

from gemetro.comfort_model import STATUS_EXTRAPOLATION, STATUS_IN_DOMAIN
from gemetro.pmv import STATUS_OUT_OF_RANGE, STATUS_VALID
from gemetro.scenario import (
    TAU_VALUES,
    Scenario,
    ScenarioError,
    outdoor_conditions,
    run_scenario,
    scenario_config,
)
from gemetro.simulator import simulate

ML_STATES = {STATUS_IN_DOMAIN, STATUS_EXTRAPOLATION}
PMV_STATES = {STATUS_VALID, STATUS_OUT_OF_RANGE}


@pytest.fixture(scope="module")
def default_record(fixture_model):
    return run_scenario(Scenario(), fixture_model)


def test_record_has_every_field_of_the_contract(default_record):
    assert set(default_record) == {
        "scenario", "outdoor", "occupancy", "met", "indoor", "ml", "pmv", "provenance",
        "sensitivity",
    }
    assert {"tin_c", "rh_in", "delta_t", "simulator_status"} <= set(default_record["indoor"])
    assert default_record["ml"]["domain_status"] in ML_STATES
    assert default_record["pmv"]["status"] in PMV_STATES


def test_every_variable_has_provenance(default_record):
    provenance = default_record["provenance"]
    for name in ("tout", "rh_out", "n", "phi_peak", "tau_r", "vel", "clo", "posture", "tin",
                 "rh_in", "ml_class", "pmv"):
        assert provenance[name]
    assert provenance["tin"] == "Simulado"
    assert provenance["ml_class"] == "Predicho"
    assert provenance["n"] == "Derivado / simulado"


def test_sweep_covers_every_tau_with_its_own_states(default_record):
    sweep = default_record["sensitivity"]
    assert [p["tau_r"] for p in sweep] == list(TAU_VALUES)
    for point in sweep:
        assert point["ml"]["domain_status"] in ML_STATES
        assert point["pmv"]["status"] in PMV_STATES
    tins = [p["tin_c"] for p in sweep]
    assert tins == sorted(tins)


def test_chain_uses_climate_occupancy_and_simulator(default_record):
    tout, rh_out = outdoor_conditions(16)
    expected = simulate(tout, rh_out, 0.75 * 300, 60)
    assert default_record["occupancy"]["n"] == pytest.approx(225.0)
    assert default_record["indoor"]["tin_c"] == pytest.approx(expected.tin)
    assert default_record["indoor"]["rh_in"] == pytest.approx(expected.rh_in)


def test_default_scenario_shows_out_of_range_states(default_record):
    # PHASE_1_ARCHITECTURE.md §9.4: the default Tin is expected above 30 °C (ISO limit).
    assert default_record["indoor"]["tin_c"] > 30
    assert default_record["pmv"]["status"] == STATUS_OUT_OF_RANGE
    assert default_record["pmv"]["value"] is None


def test_same_scenario_same_record(fixture_model):
    scenario = Scenario(line="B", hour=8, phi_peak=0.6, tau_r=30, vel=0.5, clo=0.4,
                        posture="seated")
    first = json.dumps(run_scenario(scenario, fixture_model), sort_keys=True)
    second = json.dumps(run_scenario(scenario, fixture_model), sort_keys=True)
    assert first == second


def test_advanced_mode_reports_implied_tau_and_user_assumption(fixture_model):
    record = run_scenario(Scenario(delta_t=4.0), fixture_model)
    assert record["scenario"]["mode"] == "advanced"
    assert record["indoor"]["delta_t"] == pytest.approx(4.0)
    assert record["indoor"]["tau_r_implied"] > 0
    assert record["provenance"]["delta_t"] == "Supuesto del usuario"
    # The sweep stays in normal mode (L-03).
    assert [p["tau_r"] for p in record["sensitivity"]] == list(TAU_VALUES)


@pytest.mark.parametrize(
    "change",
    [
        {"line": "C"}, {"hour": 3}, {"hour": 23}, {"phi_peak": 0.45}, {"phi_peak": 0.77},
        {"tau_r": 50}, {"vel": 1.55}, {"vel": 0.12}, {"clo": 1.05}, {"posture": "lying"},
        {"delta_t": 18.5}, {"delta_t": 0.3},
    ],
)
def test_out_of_slider_values_are_rejected(fixture_model, change):
    with pytest.raises(ScenarioError):
        run_scenario(Scenario(**change), fixture_model)


def test_config_exposes_sliders_and_defaults():
    config = scenario_config()
    assert config["sliders"]["tau_r"]["values"] == [20, 30, 45, 60, 90, 120, 180, 240]
    assert config["defaults"]["tau_r"] == 60
    assert config["prague_tau_reference_s"] == 24
