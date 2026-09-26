"""E-06: ASHRAE-augmented training, Nanjing-only evaluation.

`augmented_fit(ashrae)` is a drop-in `fit` for `select`/`nested_cv`
(`gemetro.evaluation.cv._fit` signature): for the Nanjing training rows `rows` of one inner
or outer fit call, it keeps only the ASHRAE rows inside their `ta, rh, vel, clo` domain
(`domain_filter`, eligibility step 5 of odd/tasks/e06-ashrae-augmentation.md), concatenates
them with `rows`, and fits with sample weights that keep ASHRAE's total weight equal to
Nanjing's and, when the combination calls for it, restore scikit-learn's own
`class_weight="balanced"` semantics over the weighted set (`training_weights`). `rows`
itself is never modified, and ASHRAE rows never reach a validation or test split: they exist
only inside this fit's own training data.

`build_augmented_estimator` reuses `gemetro.evaluation.candidates.build_estimator` unchanged
except for the posture encoder, which must also accept ASHRAE's `"unknown"` category; the
estimator itself is always built with `class_weight="none"`, since balancing is handled
through `model__sample_weight` instead (weights would otherwise double-count).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder

from gemetro.evaluation.candidates import LOGISTIC, NUMERIC, Combination
from gemetro.evaluation.candidates import build_estimator as _build_estimator
from gemetro.evaluation.cv import FEATURES, TARGET

POSTURE_CATEGORIES = ["seated", "standing", "unknown"]


def build_augmented_estimator(combination: Combination, config: dict) -> Pipeline:
    """`build_estimator` with a posture encoder fixed to `POSTURE_CATEGORIES`.

    Built with `class_weight="none"` regardless of `combination.class_weight`: balancing is
    applied through sample weights in `augmented_fit`, not through the estimator's own
    `class_weight` (E-06 design, "Weighting and class balance").
    """
    unweighted = replace(combination, class_weight="none")
    pipeline = _build_estimator(unweighted, config)
    encode = pipeline.named_steps["encode"]
    if combination.candidate == LOGISTIC:
        posture = OneHotEncoder(categories=[POSTURE_CATEGORIES], drop="first")
    else:
        posture = OrdinalEncoder(categories=[POSTURE_CATEGORIES])
    encode.set_params(transformers=[
        (name, posture if name == "posture" else transformer, columns)
        for name, transformer, columns in encode.transformers
    ])
    return pipeline


def domain_filter(ashrae: pd.DataFrame, train_rows: pd.DataFrame) -> pd.DataFrame:
    """ASHRAE rows inside the inclusive `ta, rh, vel, clo` range of `train_rows`.

    `train_rows` are the Nanjing training rows of one `fit` call (inner or outer); the
    held-out fold's rows never shape which ASHRAE rows are eligible for it.
    """
    mask = pd.Series(True, index=ashrae.index)
    for column in NUMERIC:
        low, high = train_rows[column].min(), train_rows[column].max()
        mask &= ashrae[column].between(low, high, inclusive="both")
    return ashrae[mask]


def training_weights(n_nanjing: int, n_ashrae: int, labels: pd.Series, class_weight: str,
                     classes: list[str]) -> np.ndarray:
    """Sample weights for one fit: `n_nanjing` Nanjing rows followed by `n_ashrae` ASHRAE rows.

    Nanjing rows weight 1; each ASHRAE row weighs `n_nanjing / n_ashrae` so ASHRAE's total
    weight equals Nanjing's (0 when there are no eligible ASHRAE rows for this fit). With
    `class_weight == "balanced"`, every weight is further multiplied by `W / (3 * W_k)`, `W`
    the total of these sample weights and `W_k` the summed weight of its own class -- computed
    from the weighted set, not from row counts, so ASHRAE's volume cannot drive it the way
    scikit-learn's own `class_weight="balanced"` (which counts rows) would.
    """
    ashrae_weight = n_nanjing / n_ashrae if n_ashrae else 0.0
    weights = np.concatenate([np.ones(n_nanjing), np.full(n_ashrae, ashrae_weight)])
    if class_weight == "balanced":
        labels = labels.to_numpy()
        total = weights.sum()
        for label in classes:
            in_class = labels == label
            class_total = weights[in_class].sum()
            if class_total > 0:
                weights[in_class] *= total / (len(classes) * class_total)
    return weights


def augmented_fit(ashrae: pd.DataFrame) -> Callable:
    """Drop-in `fit` for `select`/`nested_cv`: Nanjing `rows` plus in-domain ASHRAE rows."""

    def fit(combination: Combination, config: dict, rows: pd.DataFrame) -> Pipeline:
        in_domain = domain_filter(ashrae, rows)
        pipeline = build_augmented_estimator(combination, config)
        x = pd.concat([rows[FEATURES], in_domain[FEATURES]], ignore_index=True)
        y = pd.concat([rows[TARGET], in_domain[TARGET]], ignore_index=True)
        weights = training_weights(len(rows), len(in_domain), y, combination.class_weight,
                                   config["classes"])
        return pipeline.fit(x, y, model__sample_weight=weights)

    return fit
