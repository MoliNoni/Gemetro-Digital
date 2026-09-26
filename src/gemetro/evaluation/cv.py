"""I-13: nested, grouped cross-validation and the selection procedure.

`select(rows, days)` (PHASE_1_ARCHITECTURE.md §8.2 points 3, 5-7; L-08 to L-10):
for every preregistered combination, leave-one-day-out over `days`, training on all clean
rows of the training days and scoring macro F1 on all clean rows of the held-out day; the
best mean wins, unless the best logistic-regression combination is within one standard error
(of the best combination's fold scores) of it, in which case the logistic regression wins.

Outer loop: for each day d, select on the other four days, refit the winner on all their
clean rows and predict the rows of d. Every row gets exactly one out-of-sample prediction.
No synthetic rows are generated.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

from gemetro.evaluation.candidates import LOGISTIC, Combination, build_estimator, combinations

FEATURES = ["ta", "rh", "vel", "clo", "posture"]
TARGET = "sensation_class"


@dataclass(frozen=True)
class SelectionResult:
    chosen: Combination
    best: Combination
    best_mean: float
    best_se: float
    chosen_mean: float
    scores: dict[str, list[float]]  # combination key -> fold scores, in day order


def macro_f1(y_true, y_pred, classes) -> float:
    return float(f1_score(y_true, y_pred, labels=list(classes), average="macro",
                          zero_division=0))


def _fit(combination: Combination, config: dict, rows: pd.DataFrame):
    return build_estimator(combination, config).fit(rows[FEATURES], rows[TARGET])


def select(rows: pd.DataFrame, days: list[str], config: dict,
           candidates: list[Combination] | None = None,
           fit: Callable = _fit) -> SelectionResult:
    """Choose one combination with leave-one-day-out CV over `days` (inner loop)."""
    candidates = candidates if candidates is not None else combinations(config)
    classes = config["classes"]
    data = rows[rows["day"].isin(days)]
    scores: dict[str, list[float]] = {}
    for combination in candidates:
        fold_scores = []
        for held_out in days:
            train = data[data["day"] != held_out]
            valid = data[data["day"] == held_out]
            model = fit(combination, config, train)
            fold_scores.append(macro_f1(valid[TARGET], model.predict(valid[FEATURES]), classes))
        scores[combination.key] = fold_scores

    means = {c.key: float(np.mean(scores[c.key])) for c in candidates}
    best = max(candidates, key=lambda c: means[c.key])  # first in config order on ties
    fold = scores[best.key]
    best_se = float(np.std(fold, ddof=1) / math.sqrt(len(fold)))
    logistic = [c for c in candidates if c.candidate == LOGISTIC]
    chosen = best
    if logistic and best.candidate != LOGISTIC:
        best_lr = max(logistic, key=lambda c: means[c.key])
        if means[best.key] - means[best_lr.key] < best_se:
            chosen = best_lr
    return SelectionResult(chosen, best, means[best.key], best_se, means[chosen.key], scores)


@dataclass(frozen=True)
class OuterFold:
    day: str
    selection: SelectionResult


def nested_cv(rows: pd.DataFrame, config: dict,
              candidates: list[Combination] | None = None,
              fit: Callable = _fit) -> tuple[pd.Series, list[OuterFold]]:
    """Out-of-sample predictions (one per row, indexed like `rows`) and the outer folds."""
    days = sorted(rows["day"].unique())
    predictions = pd.Series(index=rows.index, dtype=object)
    folds = []
    for day in days:
        training_days = [d for d in days if d != day]
        selection = select(rows, training_days, config, candidates, fit)
        train = rows[rows["day"].isin(training_days)]
        test = rows[rows["day"] == day]
        model = fit(selection.chosen, config, train)
        predictions.loc[test.index] = model.predict(test[FEATURES])
        folds.append(OuterFold(day, selection))
    return predictions, folds
