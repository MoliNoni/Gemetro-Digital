"""E-05: derived thermal features and their reuse of the E-02 nested CV.

Synthetic rows are used here only to exercise the procedure; they never reach the pipeline.
"""

import math

import numpy as np
import pandas as pd
import pytest

from gemetro.evaluation.candidates import CONFIG_PATH, Combination, build_estimator, load_config
from gemetro.evaluation.cv import FEATURES, TARGET, nested_cv
from gemetro.evaluation.features import (
    DERIVED,
    VARIANTS,
    add_features,
    build_variant_estimator,
    variant_fit,
)
from gemetro.pmv import vapour_pressure

DAYS = ["d1", "d2", "d3", "d4", "d5"]
LR = Combination("logistic_regression", {"C": 1.0}, "balanced")
RF = Combination("random_forest", {"max_depth": 3, "min_samples_leaf": 5}, "balanced")
GB = Combination("gradient_boosting", {"learning_rate": 0.1, "max_depth": 2, "max_iter": 100},
                 "none")


@pytest.fixture(scope="module")
def config():
    return load_config(CONFIG_PATH)


@pytest.fixture(scope="module")
def rows():
    rng = np.random.default_rng(1)
    n = 200
    data = pd.DataFrame({
        "day": np.repeat(DAYS, n // 5),
        "ta": rng.uniform(21, 32, n), "rh": rng.uniform(52, 90, n),
        "vel": rng.uniform(0.1, 1.7, n), "clo": rng.uniform(0.2, 1.0, n),
        "posture": rng.choice(["seated", "standing"], n),
    })
    data[TARGET] = np.where(data["ta"] < 24, "cool", np.where(data["ta"] > 28, "warm", "neutral"))
    return data


def test_preregistered_variants():
    assert list(VARIANTS) == ["ta_x_rh", "ta_x_vel", "ta_x_clo", "rh_x_vel", "clo_x_standing",
                              "vapour_pressure", "sqrt_vel", "all"]
    assert VARIANTS["all"] == tuple(DERIVED)


def test_derived_values_use_inputs_only():
    x = pd.DataFrame({"ta": [25.0, 30.0], "rh": [60.0, 80.0], "vel": [0.25, 1.0],
                      "clo": [0.5, 0.4], "posture": ["seated", "standing"]})
    out = add_features(x, VARIANTS["all"])  # no label column is needed
    assert list(out.columns) == list(x.columns) + list(DERIVED)
    assert list(x.columns) == ["ta", "rh", "vel", "clo", "posture"]  # input untouched
    np.testing.assert_allclose(out["ta_x_rh"], [1500.0, 2400.0])
    np.testing.assert_allclose(out["ta_x_vel"], [6.25, 30.0])
    np.testing.assert_allclose(out["ta_x_clo"], [12.5, 12.0])
    np.testing.assert_allclose(out["rh_x_vel"], [15.0, 80.0])
    np.testing.assert_allclose(out["clo_x_standing"], [0.0, 0.4])
    np.testing.assert_allclose(out["sqrt_vel"], [0.5, 1.0])
    assert out["vapour_pressure"].tolist() == [vapour_pressure(25.0, 60.0),
                                               vapour_pressure(30.0, 80.0)]
    assert math.isclose(out["vapour_pressure"][0], 1901.5, rel_tol=1e-3)


def test_features_are_row_wise(config, rows):
    # A row's prediction does not depend on the other rows it is predicted with.
    model = build_variant_estimator(LR, config, VARIANTS["all"]).fit(rows[FEATURES], rows[TARGET])
    together = model.predict(rows[FEATURES])
    alone = [model.predict(rows[FEATURES].iloc[[i]])[0] for i in range(10)]
    assert list(together[:10]) == alone


@pytest.mark.parametrize("combination", [LR, RF, GB], ids=["lr", "rf", "gb"])
def test_no_derived_features_reproduces_the_baseline(config, rows, combination):
    base = build_estimator(combination, config).fit(rows[FEATURES], rows[TARGET])
    empty = build_variant_estimator(combination, config, ()).fit(rows[FEATURES], rows[TARGET])
    assert (base.predict(rows[FEATURES]) == empty.predict(rows[FEATURES])).all()


@pytest.mark.parametrize("variant", list(VARIANTS))
def test_every_variant_fits_every_candidate_type(config, rows, variant):
    for combination in (LR, RF, GB):
        model = variant_fit(VARIANTS[variant])(combination, config, rows)
        width = model.named_steps["encode"].transform(
            model.named_steps["derive"].transform(rows[FEATURES])).shape[1]
        assert width == 5 + len(VARIANTS[variant])
        assert set(model.predict(rows[FEATURES])) <= set(config["classes"])


def test_variant_nested_cv_is_deterministic(config, rows):
    fit = variant_fit(VARIANTS["all"])
    first, folds = nested_cv(rows, config, [LR, RF], fit)
    second, _ = nested_cv(rows, config, [LR, RF], fit)
    assert first.equals(second) and first.notna().all()
    assert [f.day for f in folds] == DAYS


def test_paired_by_day_applies_the_screening_rule():
    from gemetro.experiments.e05_thermal_features import paired_by_day

    y = ["cool", "neutral", "warm"] * 2
    rows = pd.DataFrame({
        "day": ["d1"] * 3 + ["d2"] * 3, "sensation_class": y,
        "variant": y, "reference": ["neutral"] * 6,
    })
    result = paired_by_day(rows, "variant", "reference", ["cool", "neutral", "warm"])
    assert result["f1_macro"] == 1.0 and result["delta"] > 0
    assert result["days_improved"] == 2 and all(d["improves"] for d in result["by_day"].values())
    assert result["screening"] == "Descartado"  # needs at least 4 improved days
