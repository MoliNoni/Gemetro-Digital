"""E-04: ordinal classifier and its reuse of the E-02 nested CV.

Synthetic rows are used here only to exercise the procedure; they never reach the pipeline.
"""

import numpy as np
import pandas as pd
import pytest

from gemetro.evaluation.candidates import CONFIG_PATH, Combination, build_estimator, load_config
from gemetro.evaluation.cv import FEATURES, TARGET, nested_cv, select
from gemetro.evaluation.ordinal import OrdinalClassifier, ordinal_fit
from gemetro.experiments.e04_ordinal import decide

DAYS = ["d1", "d2", "d3", "d4", "d5"]
LR = Combination("logistic_regression", {"C": 1.0}, "balanced")


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


def test_probabilities_are_a_distribution(config, rows):
    model = ordinal_fit(LR, config, rows)
    proba = model.predict_proba(rows[FEATURES])
    assert proba.shape == (len(rows), 3)
    assert (proba >= 0).all()
    np.testing.assert_allclose(proba.sum(axis=1), 1.0)


def test_two_ordered_binary_problems(config, rows):
    model = ordinal_fit(LR, config, rows)
    assert len(model.models_) == 2
    assert set(model.predict(rows[FEATURES])) <= set(config["classes"])


def test_crossing_thresholds_are_made_monotone():
    class Fixed:
        classes_ = np.array([0, 1])

        def __init__(self, p):
            self.p = p

        def predict_proba(self, x):
            return np.column_stack([1 - np.full(len(x), self.p), np.full(len(x), self.p)])

    model = OrdinalClassifier(None, ["cool", "neutral", "warm"])
    model.models_ = [Fixed(0.3), Fixed(0.6)]  # P(y > neutral) > P(y > cool): crossing
    x = pd.DataFrame({"a": [0, 1]})
    np.testing.assert_allclose(model.predict_proba(x), [[0.7, 0.0, 0.3]] * 2)
    assert list(model.predict(x)) == ["cool", "cool"]


def test_ordered_signal_is_learned(config, rows):
    model = ordinal_fit(LR, config, rows)
    assert (model.predict(rows[FEATURES]) == rows[TARGET]).mean() > 0.9


def test_unknown_label_is_rejected(config, rows):
    bad = rows.copy()
    bad.loc[bad.index[0], TARGET] = "hot"
    with pytest.raises(ValueError):
        OrdinalClassifier(build_estimator(LR, config), config["classes"]).fit(
            bad[FEATURES], bad[TARGET])


def test_reuses_nested_cv_without_leakage(config, rows):
    calls = []

    def spy(combination, cfg, train):
        calls.append(set(train["day"]))
        return ordinal_fit(combination, cfg, train)

    select(rows, DAYS[1:], config, [LR], spy)
    assert len(calls) == 4 and all("d1" not in days for days in calls)
    predictions, folds = nested_cv(rows, config, [LR], ordinal_fit)
    assert predictions.notna().all() and [f.day for f in folds] == DAYS


def test_ordinal_nested_cv_is_deterministic(config, rows):
    combos = [Combination("random_forest", {"max_depth": 3, "min_samples_leaf": 5}, "balanced"),
              Combination("gradient_boosting",
                          {"learning_rate": 0.1, "max_depth": 2, "max_iter": 100}, "none")]
    first, _ = nested_cv(rows, config, combos, ordinal_fit)
    second, _ = nested_cv(rows, config, combos, ordinal_fit)
    assert first.equals(second)


@pytest.mark.parametrize(("delta", "by_day", "low", "decision", "demonstrated"), [
    (0.02, [0.01, 0.02, 0.03, 0.01, -0.01], 0.001, "Candidato experimental", True),
    (0.02, [0.01, 0.02, 0.03, 0.01, -0.01], -0.01, "Candidato experimental", False),
    (0.02, [0.01, 0.02, -0.03, 0.01, -0.01], 0.001, "Descartado", False),
    (-0.01, [0.01, 0.02, 0.03, 0.01, 0.01], -0.05, "Descartado", False),
    (0.0, [0.01, 0.02, 0.03, 0.01, 0.01], -0.05, "Descartado", False),
])
def test_preregistered_decision_rule(delta, by_day, low, decision, demonstrated):
    result = decide(delta, by_day, low)
    assert result["decision"] == decision
    assert result["improvement_demonstrated"] is demonstrated
