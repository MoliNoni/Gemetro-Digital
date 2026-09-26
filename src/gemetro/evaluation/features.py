"""E-05: derived thermal features over the preregistered combinations.

Every derived feature is a deterministic function of the input features (never the label).
It is computed by the first pipeline step, so the fitted model still receives only
`FEATURES` and `select`/`nested_cv` run unchanged through `variant_fit(names)`.
The added features join the numeric block of `build_estimator` (standardized for the
logistic regression, passthrough for the trees).
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer

from gemetro.evaluation.candidates import NUMERIC, Combination, build_estimator
from gemetro.evaluation.cv import FEATURES, TARGET
from gemetro.pmv import vapour_pressure


def _standing(x: pd.DataFrame) -> pd.Series:
    return (x["posture"] == "standing").astype(float)


DERIVED: dict[str, Callable[[pd.DataFrame], pd.Series]] = {
    "ta_x_rh": lambda x: x["ta"] * x["rh"],
    "ta_x_vel": lambda x: x["ta"] * x["vel"],
    "ta_x_clo": lambda x: x["ta"] * x["clo"],
    "rh_x_vel": lambda x: x["rh"] * x["vel"],
    "clo_x_standing": lambda x: x["clo"] * _standing(x),
    "vapour_pressure": lambda x: pd.Series(
        [vapour_pressure(ta, rh) for ta, rh in zip(x["ta"], x["rh"], strict=True)],
        index=x.index),
    "sqrt_vel": lambda x: np.sqrt(x["vel"]),
}

# Preregistered variants (odd/tasks/e05-thermal-features.md), in report order.
VARIANTS: dict[str, tuple[str, ...]] = {
    **{name: (name,) for name in DERIVED},
    "all": tuple(DERIVED),
}


def add_features(x: pd.DataFrame, names: tuple[str, ...]) -> pd.DataFrame:
    """Copy of `x` with the named derived columns appended."""
    out = x.copy()
    for name in names:
        out[name] = DERIVED[name](x)
    return out


def build_variant_estimator(combination: Combination, config: dict,
                            names: tuple[str, ...]) -> Pipeline:
    """`build_estimator` with a derivation step and the derived columns in the numeric block."""
    base = build_estimator(combination, config)
    encode = base.named_steps["encode"]
    encode.set_params(transformers=[
        (name, transformer, NUMERIC + list(names) if name == "numeric" else columns)
        for name, transformer, columns in encode.transformers
    ])
    derive = FunctionTransformer(add_features, kw_args={"names": tuple(names)})
    return Pipeline([("derive", derive), *base.steps])


def variant_fit(names: tuple[str, ...]) -> Callable:
    """Drop-in `fit` for `select`/`nested_cv` with the named derived features."""
    def fit(combination: Combination, config: dict, rows: pd.DataFrame) -> Pipeline:
        return build_variant_estimator(combination, config, names).fit(rows[FEATURES],
                                                                      rows[TARGET])
    return fit
