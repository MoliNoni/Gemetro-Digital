"""P-11 to P-14: occupancy (I-08) and simulator v1 (I-09)."""

import itertools

import pytest

from gemetro.occupancy import C_WAGON, load_ratio, occupancy, occupancy_fraction
from gemetro.simulator import (
    CP_DRY_AIR,
    G_KG_S,
    Q_SENSIBLE_W,
    STATUS_OUTSIDE_SIMULATOR_VALIDITY,
    VOLUME_M3,
    dry_air_density,
    humidity_ratio,
    simulate,
    simulate_advanced,
)

TAU_VALUES = [20, 30, 45, 60, 90, 120, 180, 240]


# --- P-11: occupancy -----------------------------------------------------------------------


def test_peak_hour_occupancy_is_phi_peak_times_capacity():
    assert load_ratio("A", 16) == pytest.approx(1.0)
    assert occupancy("A", 16, 0.75) == pytest.approx(0.75 * C_WAGON)
    assert load_ratio("B", 17) == pytest.approx(1.0)


def test_occupancy_never_exceeds_capacity():
    for line, hour in itertools.product(["A", "B"], range(4, 23)):
        assert occupancy(line, hour, 1.0) <= C_WAGON


def test_fraction_is_capped_at_one():
    assert occupancy_fraction(0.9, 1.5) == 1.0
    assert occupancy_fraction(0.5, 0.5) == pytest.approx(0.25)


def test_unknown_hour_is_rejected():
    with pytest.raises(ValueError):
        occupancy("A", 23, 0.75)


# --- P-12: normal mode ----------------------------------------------------------------------


def test_no_passengers_means_outdoor_conditions():
    result = simulate(22.0, 0.7, 0, 60)
    assert result.tin == pytest.approx(22.0)
    assert result.w_in == pytest.approx(result.w_out)
    assert result.rh_in == pytest.approx(0.7)


def test_delta_t_is_proportional_to_n_and_tau():
    base = simulate(22.0, 0.7, 100, 60).delta_t
    assert simulate(22.0, 0.7, 200, 60).delta_t == pytest.approx(2 * base)
    assert simulate(22.0, 0.7, 100, 120).delta_t == pytest.approx(2 * base)


def test_dry_air_density_at_22c_70pct():
    assert dry_air_density(22.0, 0.7) == pytest.approx(0.98, abs=0.01)


def test_default_scenario_order_of_magnitude():
    # N = 225, τr = 60 s, V = 150 m³, ρ_as = 0.98 kg/m³ -> ΔT ≈ 6.4 K (shown as 6.5 K after
    # rounding to 0.5 °C, PHASE_1_ARCHITECTURE.md §9.4).
    mass_flow = 0.98 * VOLUME_M3 / 60
    assert 225 * Q_SENSIBLE_W / (mass_flow * CP_DRY_AIR) == pytest.approx(6.4, abs=0.05)
    result = simulate(22.0, 0.7, 225, 60)
    assert round(result.delta_t * 2) / 2 == 6.5


def test_humidity_and_temperature_share_n_over_mass_flow():
    result = simulate(22.0, 0.7, 225, 60)
    slope = (result.w_in - result.w_out) / result.delta_t
    assert slope == pytest.approx(CP_DRY_AIR * G_KG_S / Q_SENSIBLE_W)
    assert slope == pytest.approx(2.7e-4, rel=0.05)  # "≈ 2,7·10⁻⁴" in PHASE_0_REPORT.md


def test_indoor_rh_below_outdoor_rh_over_slider_ranges():
    for tout, rh_out, n, tau in itertools.product(
        [17.0, 20.0, 24.0, 27.0], [0.31, 0.5, 0.7, 0.9], [150, 225, 300], TAU_VALUES
    ):
        result = simulate(tout, rh_out, n, tau)
        if not result.outside_validity:
            assert result.rh_in < rh_out


# --- P-13: advanced mode -------------------------------------------------------------------


@pytest.mark.parametrize("tau", TAU_VALUES)
def test_implied_tau_round_trip(tau):
    normal = simulate(21.0, 0.75, 180, tau)
    advanced = simulate_advanced(21.0, 0.75, 180, normal.delta_t)
    assert advanced.tau_r == pytest.approx(tau)
    assert advanced.w_in == pytest.approx(normal.w_in)
    assert advanced.tin == pytest.approx(normal.tin)


def test_advanced_humidity_uses_delta_t_not_tau():
    result = simulate_advanced(21.0, 0.75, 180, 8.0)
    expected = humidity_ratio(0.75, 21.0) + 8.0 * CP_DRY_AIR * G_KG_S / Q_SENSIBLE_W
    assert result.w_in == pytest.approx(expected)
    assert result.mass_flow is None


# --- P-14: simulator flags -----------------------------------------------------------------


def test_tin_above_magnus_limit_is_flagged():
    result = simulate(25.0, 0.6, 300, 240)
    assert result.tin > 50
    assert result.outside_validity
    assert result.status == STATUS_OUTSIDE_SIMULATOR_VALIDITY


def test_regular_result_has_no_status():
    assert simulate(22.0, 0.7, 225, 60).status is None


def test_rh_at_saturation_is_limited_and_flagged():
    # Protection path: not reachable inside the model (no condensation), forced here.
    result = simulate_advanced(20.0, 1.05, 100, 0.0)
    assert result.rh_in == 1.0
    assert result.rh_limited
