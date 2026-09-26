"""P-15: strict ISO 7730 PMV baseline (I-10)."""

import pytest

from gemetro.pmv import (
    STATUS_OUT_OF_RANGE,
    STATUS_VALID,
    classify,
    fanger_pmv,
    pmv_baseline,
    vapour_pressure,
)

# ISO 7730:2005 Table D.1 as published (rounded to 0.1) in the validation data set
# FedericoTartarini/validation-data-comfort-models v1.0.0, ts_pmv_ppd.json (MIT).
# Inputs: ta, tr, vel, rh %, met, clo. The data set declares a PMV tolerance of 0.1 because
# the ISO two-decimal values (e.g. 0.05, 0.95) were rounded again to one decimal.
ISO_TABLE_D1 = [
    ((22, 22, 0.1, 60, 1.2, 0.5), -0.8), ((27, 27, 0.1, 60, 1.2, 0.5), 0.8),
    ((27, 27, 0.3, 60, 1.2, 0.5), 0.4), ((23.5, 25.5, 0.1, 60, 1.2, 0.5), -0.0),
    ((23.5, 25.5, 0.3, 60, 1.2, 0.5), -0.6), ((19, 19, 0.1, 40, 1.2, 1.0), -0.6),
    ((23.5, 23.5, 0.3, 40, 1.2, 1.0), 0.1), ((23, 21, 0.1, 40, 1.2, 1.0), 0.1),
    ((23, 21, 0.3, 40, 1.2, 1.0), -0.2), ((22, 22, 0.1, 60, 1.6, 0.5), 0.1),
    ((27, 27, 0.1, 60, 1.6, 0.5), 1.2), ((27, 27, 0.3, 60, 1.6, 0.5), 0.9),
]

# Unrounded PMV from an independent implementation: pythermalcomfort 4.6.0,
# pmv_ppd_iso(model="7730-2005", limit_inputs=False, round_output=False).
ORACLE = [
    ((22, 22, 0.1, 60, 1.2, 0.5), -0.7524), ((27, 27, 0.1, 60, 1.2, 0.5), 0.7653),
    ((27, 27, 0.3, 60, 1.2, 0.5), 0.4337), ((23.5, 25.5, 0.1, 60, 1.2, 0.5), -0.0132),
    ((23.5, 25.5, 0.3, 60, 1.2, 0.5), -0.5551), ((19, 19, 0.1, 40, 1.2, 1.0), -0.5984),
    ((23.5, 23.5, 0.3, 40, 1.2, 1.0), 0.1216), ((23, 21, 0.1, 40, 1.2, 1.0), 0.0526),
    ((23, 21, 0.3, 40, 1.2, 1.0), -0.1662), ((22, 22, 0.1, 60, 1.6, 0.5), 0.0474),
    ((27, 27, 0.1, 60, 1.6, 0.5), 1.1713), ((27, 27, 0.3, 60, 1.6, 0.5), 0.9509),
    ((25, 25, 0.3, 70, 1.0, 0.5), -0.7900), ((25, 25, 0.3, 70, 1.2, 0.5), -0.2065),
    ((29.5, 29.5, 0.9, 55, 1.2, 0.3), 0.5776), ((21.2, 21.2, 0.15, 60, 1.0, 1.0), -0.6264),
    ((26.4, 26.4, 0.62, 75, 1.0, 0.36), -1.0726), ((28, 28, 0.05, 50, 1.2, 0.2), 0.6168),
    ((24, 24, 1.0, 80, 1.0, 0.8), -0.7545),
]


@pytest.mark.parametrize(("inputs", "expected"), ISO_TABLE_D1)
def test_iso_7730_table_d1_at_published_precision(inputs, expected):
    assert fanger_pmv(*inputs) == pytest.approx(expected, abs=0.1)


@pytest.mark.parametrize(("inputs", "expected"), ORACLE)
def test_matches_independent_implementation_within_0_01(inputs, expected):
    assert fanger_pmv(*inputs) == pytest.approx(expected, abs=0.01)


def test_met_from_posture_and_tr_equals_ta():
    seated = pmv_baseline(25, 70, 0.3, 0.5, "seated")
    standing = pmv_baseline(25, 70, 0.3, 0.5, "standing")
    assert seated.pmv == pytest.approx(fanger_pmv(25, 25, 0.3, 70, 1.0, 0.5))
    assert standing.pmv == pytest.approx(fanger_pmv(25, 25, 0.3, 70, 1.2, 0.5))


@pytest.mark.parametrize(
    ("kwargs", "reason"),
    [
        ({"ta": 30.01}, "ta"),
        ({"ta": 9.99}, "ta"),
        ({"vel": 1.01}, "vel"),
        ({"clo": 2.01}, "clo"),
        ({"ta": 28.0, "rh_percent": 80.0}, "pa"),
    ],
)
def test_inputs_just_outside_the_iso_ranges_are_out_of_range(kwargs, reason):
    args = {"ta": 24.0, "rh_percent": 50.0, "vel": 0.2, "clo": 0.5, "posture": "seated"}
    result = pmv_baseline(**{**args, **kwargs})
    assert result.status == STATUS_OUT_OF_RANGE
    assert result.pmv is None and result.pmv_class is None
    assert reason in result.reasons


@pytest.mark.parametrize(
    "kwargs", [{"ta": 30.0, "rh_percent": 40.0}, {"vel": 1.0}, {"clo": 0.0, "ta": 30.0, "rh_percent": 40.0}])
def test_inputs_on_the_iso_limits_are_valid(kwargs):
    args = {"ta": 24.0, "rh_percent": 50.0, "vel": 0.2, "clo": 0.5, "posture": "standing"}
    assert pmv_baseline(**{**args, **kwargs}).status == STATUS_VALID


def test_pa_limit_uses_iso_vapour_pressure():
    assert vapour_pressure(25.0, 100.0) == pytest.approx(3167, abs=2)


def test_pmv_outside_minus2_plus2_is_not_reported():
    result = pmv_baseline(12.0, 50.0, 0.8, 0.2, "seated")
    assert result.status == STATUS_OUT_OF_RANGE
    assert result.reasons == ("pmv",)
    assert result.pmv is None


@pytest.mark.parametrize(
    ("pmv", "label"),
    [(-0.51, "cool"), (-0.5, "neutral"), (0.0, "neutral"), (0.5, "neutral"), (0.51, "warm")],
)
def test_class_boundaries(pmv, label):
    assert classify(pmv) == label
