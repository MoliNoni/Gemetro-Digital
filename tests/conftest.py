"""Shared test fixtures.

The comfort model fixture is a TEST DOUBLE trained on synthetic rows. It only exercises the
artifact contract; its predictions mean nothing and it is never written to artifacts/.
"""

import numpy as np
import pandas as pd
import pytest
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from gemetro.comfort_model import NUMERIC_FEATURES, ComfortModel, Domain, save_artifact

# Domain documented in DATA_AUDIT.md for the final Nanjing rows.
AUDIT_DOMAIN = {
    "ta": {"min": 21.07, "max": 31.63},
    "rh": {"min": 52.05, "max": 89.47},
    "vel": {"min": 0.08, "max": 1.72},
    "clo": {"min": 0.17, "max": 1.06},
    "postures": ["seated", "standing"],
}


def _synthetic_estimator():
    rng = np.random.default_rng(0)
    n = 300
    rows = pd.DataFrame(
        {
            "ta": rng.uniform(21, 32, n),
            "rh": rng.uniform(52, 90, n),
            "vel": rng.uniform(0.1, 1.7, n),
            "clo": rng.uniform(0.2, 1.0, n),
            "posture": rng.choice(["seated", "standing"], n),
        }
    )
    labels = np.where(rows["ta"] < 24, "cool", np.where(rows["ta"] > 28, "warm", "neutral"))
    pipeline = Pipeline(
        [
            ("encode", ColumnTransformer(
                [("posture", OneHotEncoder(), ["posture"])], remainder="passthrough"
            )),
            ("model", LogisticRegression(max_iter=1000)),
        ]
    )
    return pipeline.fit(rows[NUMERIC_FEATURES + ["posture"]], labels)


@pytest.fixture(scope="session")
def fixture_model_dir(tmp_path_factory):
    directory = tmp_path_factory.mktemp("comfort_model")
    save_artifact(
        _synthetic_estimator(),
        Domain.from_dict(AUDIT_DOMAIN),
        {"kind": "synthetic test double"},
        directory,
    )
    return directory


@pytest.fixture(scope="session")
def fixture_model(fixture_model_dir):
    return ComfortModel.load(fixture_model_dir)
