"""Guided mode service (GUIDED_MODE.md §3): periods, τr selection and fallback."""

import pytest

from gemetro.comfort_model import STATUS_EXTRAPOLATION, STATUS_IN_DOMAIN
from gemetro.guided import (
    FIXED,
    GUIDED_TAU_PROVENANCE,
    SELECTED_FALLBACK,
    SELECTED_IN_DOMAIN,
    period_hours,
    run_guided,
    select_tau_r,
)
from gemetro.scenario import TAU_VALUES, Scenario, ScenarioError, run_scenario
from gemetro.simulator import STATUS_OUTSIDE_SIMULATOR_VALIDITY


def _sweep(in_domain=(), outside_simulator=()):
    return [
        {
            "tau_r": tau,
            "simulator_status": STATUS_OUTSIDE_SIMULATOR_VALIDITY if tau in outside_simulator
            else None,
            "ml": {"domain_status": STATUS_IN_DOMAIN if tau in in_domain
                   else STATUS_EXTRAPOLATION},
        }
        for tau in TAU_VALUES
    ]


def test_periods_have_the_closed_hours():
    assert period_hours("morning") == list(range(4, 11))
    assert period_hours("midday") == [11, 12, 13, 14]
    assert period_hours("afternoon") == [15, 16, 17, 18]
    assert period_hours("night") == [19, 20, 21, 22]


def test_fixed_parameters_are_the_phase_1_defaults_with_seated_posture():
    # posture is "seated" as a guided-mode-only scenario assumption (direction 2026-09-25);
    # scenario.py DEFAULTS["posture"] stays "standing" for simulation mode, unchanged.
    assert FIXED == {"phi_peak": 0.75, "vel": 0.3, "clo": 0.5, "posture": "seated"}


@pytest.mark.parametrize(
    ("in_domain", "outside_simulator", "expected"),
    [
        (TAU_VALUES, (), (60, SELECTED_IN_DOMAIN, 8)),
        ((20, 45, 240), (), (45, SELECTED_IN_DOMAIN, 3)),
        ((30, 90), (), (30, SELECTED_IN_DOMAIN, 2)),  # tie at 30 s: the shorter τr wins
        ((240,), (), (240, SELECTED_IN_DOMAIN, 1)),
        ((45, 60), (60,), (45, SELECTED_IN_DOMAIN, 1)),  # simulator validity is required
        ((), (), (60, SELECTED_FALLBACK, 0)),
    ],
)
def test_tau_r_selection_is_deterministic(in_domain, outside_simulator, expected):
    assert select_tau_r(_sweep(in_domain, outside_simulator)) == expected


@pytest.mark.parametrize("line", ["A", "B"])
def test_midday_has_no_coverage_and_is_labelled_as_fallback(fixture_model, line):
    # GUIDED_MODE.md §2: at 11-14 h the indoor RH falls below the domain minimum.
    for entry in run_guided(line, "midday", fixture_model)["entries"]:
        assert entry["coverage"] == {"in_domain": 0, "total": 8}
        assert entry["selection"] == SELECTED_FALLBACK
        assert entry["selected_tau_r"] == 60
        assert entry["record"]["scenario"]["tau_r"] == 60
        assert entry["record"]["ml"]["domain_status"] == STATUS_EXTRAPOLATION
        assert "rh" in entry["record"]["ml"]["out_of_domain"]


def test_entry_record_is_the_scenario_record_for_the_selected_tau_r(fixture_model):
    guided = run_guided("A", "afternoon", fixture_model)
    assert guided["hours"] == [15, 16, 17, 18]
    for entry in guided["entries"]:
        expected = run_scenario(
            Scenario(line="A", hour=entry["hour"], tau_r=entry["selected_tau_r"], **FIXED),
            fixture_model,
        )
        expected["provenance"]["tau_r"] = GUIDED_TAU_PROVENANCE
        assert entry["record"] == expected
        in_domain = sum(
            point["ml"]["domain_status"] == STATUS_IN_DOMAIN and point["simulator_status"] is None
            for point in entry["record"]["sensitivity"]
        )
        assert entry["coverage"]["in_domain"] == in_domain


def test_only_line_hour_and_tau_r_vary(fixture_model):
    for entry in run_guided("B", "morning", fixture_model)["entries"]:
        scenario = entry["record"]["scenario"]
        assert {k: scenario[k] for k in FIXED} == FIXED
        assert scenario["line"] == "B"
        assert scenario["mode"] == "normal"


def test_same_request_same_result(fixture_model):
    assert run_guided("B", "night", fixture_model) == run_guided("B", "night", fixture_model)


@pytest.mark.parametrize(("line", "period"), [("C", "morning"), ("A", "evening")])
def test_invalid_line_or_period_is_rejected(fixture_model, line, period):
    with pytest.raises(ScenarioError):
        run_guided(line, period, fixture_model)
