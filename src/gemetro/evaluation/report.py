"""I-14: metrics of the ML vs PMV comparison (PHASE_1_ARCHITECTURE.md §8.1-8.2).

Comparison rows: the ISO 7730 valid rows only, the same rows for both models, with the ML
out-of-sample predictions. Primary metric: macro F1; Δ = F1_ML - F1_PMV.
Uncertainty: paired bootstrap resampling shared-measurement-window groups (not rows),
percentile interval; Δ per day as a contrast. ML performance on the out-of-range rows is
descriptive only ("sin comparación posible con el PMV").
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    precision_score,
    recall_score,
)

from gemetro.evaluation.cv import macro_f1

VERDICT_ML_BETTER = "El ML supera al PMV"
VERDICT_NOT_SHOWN = "No se demuestra superioridad"
VERDICT_PMV_BETTER = "El resultado favorece al PMV"
NO_COMPARISON = "sin comparación posible con el PMV"


def classification_metrics(y_true: pd.Series, y_pred: pd.Series, classes: list[str]) -> dict:
    """Secondary metrics of one classifier on one set of rows."""
    labels = list(classes)
    opposite = int(((y_true == "cool") & (y_pred == "warm")).sum()
                   + ((y_true == "warm") & (y_pred == "cool")).sum())
    return {
        "rows": len(y_true),
        "f1_macro": macro_f1(y_true, y_pred, labels),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "recall": dict(zip(labels, recall_score(y_true, y_pred, labels=labels, average=None,
                                                  zero_division=0).tolist(), strict=True)),
        "precision": dict(zip(labels, precision_score(y_true, y_pred, labels=labels, average=None,
                                                        zero_division=0).tolist(), strict=True)),
        "confusion_matrix": {
            "labels": labels,
            "rows_true_columns_predicted": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        },
        "opposite_errors": opposite,
    }


def paired_bootstrap(y_true: np.ndarray, ml: np.ndarray, pmv: np.ndarray, groups: np.ndarray,
                     classes: list[str], replicates: int, level: float, seed: int) -> dict:
    """Percentile interval of Δ, resampling whole groups with replacement."""
    rng = np.random.default_rng(seed)
    unique, inverse = np.unique(groups, return_inverse=True)
    members = [np.flatnonzero(inverse == g) for g in range(len(unique))]
    deltas = np.empty(replicates)
    for r in range(replicates):
        picked = rng.integers(0, len(unique), len(unique))
        idx = np.concatenate([members[g] for g in picked])
        deltas[r] = macro_f1(y_true[idx], ml[idx], classes) - macro_f1(y_true[idx], pmv[idx], classes)
    alpha = (1 - level) / 2
    low, high = np.quantile(deltas, [alpha, 1 - alpha])
    return {"low": float(low), "high": float(high), "replicates": replicates,
            "groups": len(unique), "level": level}


def verdict(low: float, high: float) -> str:
    if low > 0:
        return VERDICT_ML_BETTER
    if high < 0:
        return VERDICT_PMV_BETTER
    return VERDICT_NOT_SHOWN


def compare(table: pd.DataFrame, config: dict) -> dict:
    """Full E-02 report from the final table with the out-of-sample column `ml_prediction`."""
    classes = config["classes"]
    valid = table[table["iso_valid"]]
    y, ml, pmv = valid["sensation_class"], valid["ml_prediction"], valid["pmv_class"]
    f1_ml, f1_pmv = macro_f1(y, ml, classes), macro_f1(y, pmv, classes)
    boot = config["bootstrap"]
    interval = paired_bootstrap(
        y.to_numpy(), ml.to_numpy(), pmv.to_numpy(), valid["window_group"].to_numpy(), classes,
        boot["replicates"], boot["level"], config["seed"],
    )
    per_day = {}
    for day, rows in valid.groupby("day"):
        d_ml = macro_f1(rows["sensation_class"], rows["ml_prediction"], classes)
        d_pmv = macro_f1(rows["sensation_class"], rows["pmv_class"], classes)
        per_day[day] = {"rows": len(rows), "f1_ml": d_ml, "f1_pmv": d_pmv,
                        "delta": d_ml - d_pmv}
    always_neutral = pd.Series("neutral", index=y.index)
    out = table[~table["iso_valid"]]
    return {
        "comparison_rows": len(valid),
        "f1_macro_ml": f1_ml,
        "f1_macro_pmv": f1_pmv,
        "delta": f1_ml - f1_pmv,
        "delta_ci": interval,
        "verdict": verdict(interval["low"], interval["high"]),
        "delta_by_day": per_day,
        "ml": classification_metrics(y, ml, classes),
        "pmv": classification_metrics(y, pmv, classes),
        "always_neutral_accuracy": float(accuracy_score(y, always_neutral)),
        "ml_on_iso_out_of_range_rows": {
            "label": NO_COMPARISON,
            **classification_metrics(out["sensation_class"], out["ml_prediction"], classes),
        },
    }
