"""E-06: ASHRAE loading, domain filtering, sample weights and the augmented fit.

Synthetic rows are used here only to exercise the procedure; they never reach the pipeline.
"""

import math

import numpy as np
import pandas as pd
import pytest

from gemetro.data.ashrae import load_ashrae
from gemetro.evaluation.augment import augmented_fit, domain_filter, training_weights
from gemetro.evaluation.candidates import CONFIG_PATH, Combination, build_estimator, load_config
from gemetro.evaluation.cv import FEATURES, TARGET, nested_cv

DAYS = ["d1", "d2", "d3", "d4", "d5"]
LR = Combination("logistic_regression", {"C": 1.0}, "balanced")
RF = Combination("random_forest", {"max_depth": 3, "min_samples_leaf": 5}, "balanced")
GB = Combination("gradient_boosting", {"learning_rate": 0.1, "max_depth": 2, "max_iter": 100},
                 "none")


@pytest.fixture(scope="module")
def config():
    return load_config(CONFIG_PATH)


def _labelled(rows: pd.DataFrame) -> pd.DataFrame:
    rows = rows.copy()
    rows[TARGET] = np.where(rows["ta"] < 24, "cool", np.where(rows["ta"] > 28, "warm", "neutral"))
    return rows


@pytest.fixture(scope="module")
def nanjing_rows():
    rng = np.random.default_rng(2)
    n = 200
    data = pd.DataFrame({
        "day": np.repeat(DAYS, n // 5),
        "ta": rng.uniform(21, 32, n), "rh": rng.uniform(52, 90, n),
        "vel": rng.uniform(0.1, 1.7, n), "clo": rng.uniform(0.2, 1.0, n),
        "posture": rng.choice(["seated", "standing"], n),
    })
    return _labelled(data)


@pytest.fixture(scope="module")
def ashrae_rows():
    rng = np.random.default_rng(3)
    n = 40
    data = pd.DataFrame({
        "ta": rng.uniform(21, 32, n), "rh": rng.uniform(52, 90, n),
        "vel": rng.uniform(0.1, 1.7, n), "clo": rng.uniform(0.2, 1.0, n),
        "posture": ["unknown"] * n,
    })
    return _labelled(data)


# --- domain_filter -----------------------------------------------------------------------


def test_domain_filter_keeps_inclusive_range_only():
    train_rows = pd.DataFrame({"ta": [20.0, 30.0], "rh": [50.0, 90.0],
                               "vel": [0.1, 1.5], "clo": [0.2, 1.0]})
    ashrae = pd.DataFrame({
        "ta": [20.0, 30.0, 19.9, 30.1, 25.0],
        "rh": [50.0, 90.0, 50.0, 90.0, 50.0],
        "vel": [0.1, 1.5, 0.1, 1.5, 0.1],
        "clo": [0.2, 1.0, 0.2, 1.0, 0.2],
    })
    kept = domain_filter(ashrae, train_rows)
    assert kept.index.tolist() == [0, 1, 4]  # boundaries kept, just-outside rows dropped


# --- training_weights ---------------------------------------------------------------------


def test_training_weights_ashrae_total_equals_nanjing_total():
    labels = pd.Series(["cool", "cool", "warm", "warm", "neutral", "neutral"])
    weights = training_weights(4, 2, labels, "none", ["cool", "neutral", "warm"])
    assert weights[:4].tolist() == [1.0, 1.0, 1.0, 1.0]
    assert weights[4:].tolist() == [2.0, 2.0]
    assert math.isclose(weights[:4].sum(), weights[4:].sum())


def test_training_weights_balanced_equalises_summed_class_weight():
    labels = pd.Series(["cool", "cool", "cool", "warm", "neutral", "neutral"])
    weights = training_weights(4, 2, labels, "balanced", ["cool", "neutral", "warm"])
    labels_arr = labels.to_numpy()
    totals = {c: weights[labels_arr == c].sum() for c in ("cool", "neutral", "warm")}
    assert math.isclose(totals["cool"], totals["neutral"])
    assert math.isclose(totals["neutral"], totals["warm"])


def test_training_weights_handles_zero_eligible_ashrae():
    labels = pd.Series(["cool", "warm", "neutral", "neutral"])
    weights = training_weights(4, 0, labels, "none", ["cool", "neutral", "warm"])
    assert weights.tolist() == [1.0, 1.0, 1.0, 1.0]


# --- augmented_fit / nested_cv --------------------------------------------------------------


def test_predictions_are_nanjing_only(config, nanjing_rows, ashrae_rows):
    predictions, folds = nested_cv(nanjing_rows, config, [LR, RF], augmented_fit(ashrae_rows))
    assert predictions.index.equals(nanjing_rows.index)
    assert len(predictions) == len(nanjing_rows)  # no ASHRAE row ever gets a prediction slot
    assert predictions.notna().all()
    assert [f.day for f in folds] == DAYS


@pytest.mark.parametrize("combination", [LR, RF, GB], ids=["lr", "rf", "gb"])
def test_posture_unknown_accepted_by_every_candidate_type(config, nanjing_rows, ashrae_rows,
                                                          combination):
    fit = augmented_fit(ashrae_rows)
    train = nanjing_rows[nanjing_rows["day"] != "d1"]
    test = nanjing_rows[nanjing_rows["day"] == "d1"]
    model = fit(combination, config, train)
    predictions = model.predict(test[FEATURES])  # Nanjing test rows: always seated/standing
    assert set(predictions) <= set(config["classes"])
    unknown_row = pd.DataFrame({"ta": [25.0], "rh": [60.0], "vel": [0.5], "clo": [0.5],
                                "posture": ["unknown"]})
    assert model.predict(unknown_row)[0] in config["classes"]


@pytest.mark.parametrize("combination", [LR, RF], ids=["lr", "rf"])
def test_empty_ashrae_reproduces_balanced_class_weight(config, nanjing_rows, combination):
    empty_ashrae = pd.DataFrame(columns=["ta", "rh", "vel", "clo", "posture", TARGET])
    train = nanjing_rows[nanjing_rows["day"] != "d1"]
    test = nanjing_rows[nanjing_rows["day"] == "d1"]

    augmented_model = augmented_fit(empty_ashrae)(combination, config, train)
    base_model = build_estimator(combination, config).fit(train[FEATURES], train[TARGET])

    np.testing.assert_array_equal(augmented_model.predict(test[FEATURES]),
                                  base_model.predict(test[FEATURES]))


# --- load_ashrae ---------------------------------------------------------------------------


def _write_ashrae_csvs(tmp_path):
    measurements = pd.DataFrame({
        "building_id": [1, 1, 1, 2, 3, 4, 5],
        "ta": [25.0, 26.0, 27.0, 24.0, 28.0, None, 29.0],
        "rh": [60.0, 55.0, 50.0, 65.0, 70.0, 62.0, 58.0],
        "vel": [0.2, 0.3, 0.25, 0.4, 0.15, 0.35, 0.3],
        "clo": [0.5, 0.5, 0.6, 0.5, 0.45, 0.55, 0.5],
        # idx0/1: kept (cool/neutral); idx2: non-integer -> dropped; idx3: QA fail -> dropped;
        # idx4: kept (cool); idx5: missing ta -> dropped; idx6: kept (warm).
        "thermal_sensation": [-1.0, 0.0, 1.5, 2.0, -2.0, 1.0, 3.0],
    })
    metadata = pd.DataFrame({
        "building_id": [1, 2, 3, 4, 5],
        "quality_assurance": ["pass", "fail", "pass", "pass", "pass"],
    })
    m_path = tmp_path / "measurements.csv.gz"
    meta_path = tmp_path / "metadata.csv"
    measurements.to_csv(m_path, index=False, compression="gzip")
    metadata.to_csv(meta_path, index=False)
    return m_path, meta_path


def test_load_ashrae_applies_every_eligibility_rule(tmp_path):
    m_path, meta_path = _write_ashrae_csvs(tmp_path)
    result = load_ashrae(m_path, meta_path)
    assert len(result) == 4
    assert set(result.columns) == {"ta", "rh", "vel", "clo", "posture", "sensation_class"}
    assert (result["posture"] == "unknown").all()  # explicit marker, never derived
    assert sorted(result["sensation_class"].tolist()) == ["cool", "cool", "neutral", "warm"]
