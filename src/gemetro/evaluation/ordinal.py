"""E-04: ordinal classification over the preregistered combinations (Frank & Hall).

For the ordered classes `cool < neutral < warm` the same base pipeline of a combination is
fitted on two ordered binary problems, `y > cool` and `y > neutral`. With p1 = P(y > cool)
and p2 = min(P(y > neutral), p1):

    P(cool) = 1 - p1,  P(neutral) = p1 - p2,  P(warm) = p2

and the prediction is the argmax (ties go to the lower class). `ordinal_fit` has the
signature of `gemetro.evaluation.cv._fit`, so `select` and `nested_cv` run unchanged.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import clone

from gemetro.evaluation.candidates import Combination, build_estimator
from gemetro.evaluation.cv import FEATURES, TARGET


class OrdinalClassifier:
    """K-1 cumulative binary models over classes given in their natural order."""

    def __init__(self, base, classes: list[str]):
        self.base = base
        self.classes = list(classes)

    def fit(self, x: pd.DataFrame, y: pd.Series) -> OrdinalClassifier:
        rank = pd.Series(y).map({c: i for i, c in enumerate(self.classes)}).to_numpy()
        if np.isnan(rank.astype(float)).any():
            raise ValueError("target contains labels outside the ordered classes")
        self.models_ = [clone(self.base).fit(x, (rank > k).astype(int))
                        for k in range(len(self.classes) - 1)]
        return self

    def predict_proba(self, x: pd.DataFrame) -> np.ndarray:
        above = np.column_stack([m.predict_proba(x)[:, list(m.classes_).index(1)]
                                 for m in self.models_])
        above = np.minimum.accumulate(above, axis=1)  # P(y > k) non-increasing in k
        ones = np.ones((len(above), 1))
        zeros = np.zeros((len(above), 1))
        cumulative = np.hstack([ones, above, zeros])  # P(y > k-1) for k = 0..K
        return cumulative[:, :-1] - cumulative[:, 1:]

    def predict(self, x: pd.DataFrame) -> np.ndarray:
        return np.array(self.classes, dtype=object)[self.predict_proba(x).argmax(axis=1)]


def ordinal_fit(combination: Combination, config: dict, rows: pd.DataFrame) -> OrdinalClassifier:
    """Drop-in `fit` for `select`/`nested_cv`: the ordinal version of one combination."""
    base = build_estimator(combination, config)
    return OrdinalClassifier(base, config["classes"]).fit(rows[FEATURES], rows[TARGET])
