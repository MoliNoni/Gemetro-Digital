"""P-17 to P-20: nested CV, selection rule, bootstrap and determinism (I-12 to I-14).

Synthetic rows are used here only to exercise the procedure; they never reach the pipeline.
"""

import numpy as np
import pandas as pd
import pytest

from gemetro.evaluation.candidates import (
    CONFIG_PATH,
    Combination,
    build_estimator,
    combinations,
    load_config,
)
from gemetro.evaluation.cv import FEATURES, nested_cv, select
from gemetro.evaluation.report import (
    VERDICT_ML_BETTER,
    VERDICT_NOT_SHOWN,
    VERDICT_PMV_BETTER,
    compare,
    paired_bootstrap,
    verdict,
)

DAYS = ["d1", "d2", "d3", "d4", "d5"]


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
    data["sensation_class"] = np.where(data["ta"] < 24, "cool",
                                       np.where(data["ta"] > 28, "warm", "neutral"))
    return data


def test_preregistered_grid_sizes(config):
    combos = combinations(config)
    by_candidate = pd.Series([c.candidate for c in combos]).value_counts().to_dict()
    assert by_candidate == {"logistic_regression": 8, "random_forest": 18,
                            "gradient_boosting": 16}
    assert config["seed"] == 20250925
    assert config["bootstrap"]["replicates"] == 10000


def test_every_combination_builds(config):
    for combination in combinations(config):
        build_estimator(combination, config)


class _Spy:
    """Fit function recording the training days of every fit."""

    def __init__(self, config):
        self.config = config
        self.calls = []

    def __call__(self, combination, config, train):
        self.calls.append(set(train["day"]))
        return build_estimator(combination, config).fit(train[FEATURES], train["sensation_class"])


def test_no_leakage_of_the_outer_day(config, rows):
    # P-17: in every outer fold the test day never appears in any fit.
    combos = [Combination("logistic_regression", {"C": 1.0}, "none")]
    for day in DAYS:
        spy = _Spy(config)
        training_days = [d for d in DAYS if d != day]
        select(rows, training_days, config, combos, spy)
        assert spy.calls, "no fit happened"
        assert all(day not in days for days in spy.calls)
        assert len(spy.calls) == 4  # inner leave-one-day-out over four days (L-09)


def test_one_out_of_sample_prediction_per_row(config, rows):
    # P-18
    combos = [Combination("logistic_regression", {"C": 1.0}, "none")]
    predictions, folds = nested_cv(rows, config, combos)
    assert predictions.notna().all()
    assert predictions.index.equals(rows.index)
    assert [f.day for f in folds] == DAYS


def test_logistic_wins_within_one_standard_error(config, rows):
    combos = [Combination("logistic_regression", {"C": 1.0}, "none"),
              Combination("random_forest", {"max_depth": 3, "min_samples_leaf": 1}, "none")]
    result = select(rows, DAYS[:4], config, combos)
    means = {k: np.mean(v) for k, v in result.scores.items()}
    lr_key, rf_key = combos[0].key, combos[1].key
    if means[rf_key] > means[lr_key] and means[rf_key] - means[lr_key] < result.best_se:
        assert result.chosen.candidate == "logistic_regression"
    assert result.chosen.key in means


def test_selection_rule_on_known_scores(config, rows):
    """The rule itself, with fold scores forced through a fake fit."""
    lr = Combination("logistic_regression", {"C": 1.0}, "none")
    rf = Combination("random_forest", {"max_depth": 3, "min_samples_leaf": 1}, "none")

    class Const:
        def __init__(self, label):
            self.label = label

        def predict(self, x):
            return np.array([self.label] * len(x))

    # RF predicts the majority class of each validation day perfectly? Use constant models:
    # both get the same score, so RF is never better by a full SE and LR must win ties.
    result = select(rows, DAYS[:4], config, [rf, lr], lambda c, cfg, t: Const("neutral"))
    assert result.chosen.candidate == "logistic_regression"


def test_bootstrap_resamples_groups_and_is_deterministic():
    # P-19 / P-20
    y = np.array(["cool", "neutral", "warm", "neutral"] * 25)
    ml = y.copy()
    pmv = np.array(["neutral"] * 100)
    groups = np.repeat(np.arange(50), 2)
    a = paired_bootstrap(y, ml, pmv, groups, ["cool", "neutral", "warm"], 200, 0.95, 7)
    b = paired_bootstrap(y, ml, pmv, groups, ["cool", "neutral", "warm"], 200, 0.95, 7)
    assert a == b
    assert a["groups"] == 50
    assert a["low"] > 0


@pytest.mark.parametrize(("low", "high", "expected"), [
    (0.01, 0.2, VERDICT_ML_BETTER), (-0.1, 0.2, VERDICT_NOT_SHOWN),
    (-0.3, -0.01, VERDICT_PMV_BETTER), (0.0, 0.2, VERDICT_NOT_SHOWN),
])
def test_verdict_rule(low, high, expected):
    assert verdict(low, high) == expected


def test_comparison_uses_only_iso_valid_rows_for_both_models(config):
    table = pd.DataFrame({
        "day": ["d1"] * 6, "window_group": [0, 1, 2, 3, 4, 5],
        "sensation_class": ["cool", "neutral", "warm", "neutral", "warm", "cool"],
        "ml_prediction": ["cool", "neutral", "warm", "neutral", "cool", "warm"],
        "pmv_class": ["cool", "cool", "warm", "neutral", None, None],
        "iso_valid": [True, True, True, True, False, False],
    })
    cfg = {**config, "bootstrap": {**config["bootstrap"], "replicates": 50}}
    report = compare(table, cfg)
    assert report["comparison_rows"] == 4
    assert report["ml"]["rows"] == report["pmv"]["rows"] == 4
    assert report["ml_on_iso_out_of_range_rows"]["rows"] == 2
    assert report["ml_on_iso_out_of_range_rows"]["opposite_errors"] == 2


def test_nested_cv_is_deterministic(config, rows):
    # P-20
    combos = [Combination("random_forest", {"max_depth": 3, "min_samples_leaf": 5}, "balanced"),
              Combination("gradient_boosting",
                          {"learning_rate": 0.1, "max_depth": 2, "max_iter": 100}, "none")]
    first, _ = nested_cv(rows, config, combos)
    second, _ = nested_cv(rows, config, combos)
    assert first.equals(second)
