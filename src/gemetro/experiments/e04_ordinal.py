"""E-04: ordinal classification vs the E-02 baseline (experimental; official model untouched).

Same protocol as E-02: the 882 clean rows of data/interim/nanjing_final.csv, the preregistered
config/evaluation.toml grid, nested leave-one-day-out with the 1-SE rule (`nested_cv`), with
every combination fitted as an ordinal classifier (`ordinal_fit`). The comparison is paired
with E-02's out-of-sample predictions on the same 608 ISO-valid rows; the out-of-range rows
are descriptive only. Decision rule (odd/tasks/e04-ordinal-classification.md, fixed before
running): candidate iff pooled Δ > 0 and per-day Δ > 0 on at least 4 of 5 days.

Inputs: data/interim/nanjing_final.csv (E-01), data/interim/e02_oof_predictions.csv (E-02).
Outputs:
- data/interim/e04_oof_predictions.csv: one ordinal out-of-sample prediction per row (local);
- reports/evaluation/e04_ordinal.json: metrics, Δ with its interval, per-day results and the
  decision (versioned).
"""

from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, balanced_accuracy_score

from gemetro.evaluation.candidates import CONFIG_PATH, config_sha256, load_config
from gemetro.evaluation.cv import macro_f1, nested_cv
from gemetro.evaluation.ordinal import ordinal_fit
from gemetro.evaluation.report import NO_COMPARISON, classification_metrics, paired_bootstrap
from gemetro.experiments.e01_nanjing_final_set import FINAL_TABLE
from gemetro.experiments.e02_ml_vs_pmv import OOF_TABLE as E02_OOF_TABLE
from gemetro.paths import DATA_INTERIM, REPORTS

OOF_TABLE = DATA_INTERIM / "e04_oof_predictions.csv"
E04_REPORT = REPORTS / "evaluation" / "e04_ordinal.json"
BASELINE_F1 = 0.38939645357260594  # reports/evaluation/e02_ml_vs_pmv.json, f1_macro_ml
MIN_DAYS_IMPROVED = 4

CANDIDATE = "Candidato experimental"
DISCARDED = "Descartado"


def _day_metrics(y, pred, classes) -> dict:
    return {"f1_macro": macro_f1(y, pred, classes),
            "accuracy": float(accuracy_score(y, pred)),
            "balanced_accuracy": float(balanced_accuracy_score(y, pred))}


def _spread(values: list[float]) -> dict:
    return {"mean": float(np.mean(values)), "std": float(np.std(values, ddof=1)),
            "min": float(np.min(values)), "max": float(np.max(values))}


def decide(delta: float, delta_by_day: list[float], ci_low: float) -> dict:
    improved_days = sum(d > 0 for d in delta_by_day)
    candidate = delta > 0 and improved_days >= MIN_DAYS_IMPROVED
    return {"decision": CANDIDATE if candidate else DISCARDED,
            "days_improved": improved_days,
            "improvement_demonstrated": bool(candidate and ci_low > 0)}


def compare_with_baseline(table: pd.DataFrame, config: dict) -> dict:
    """Paired report on the ISO-valid rows; `ordinal` and `baseline` are OOF columns."""
    classes = config["classes"]
    valid = table[table["iso_valid"]]
    y, ordi, base = valid["sensation_class"], valid["ordinal"], valid["baseline"]
    f1_ord, f1_base = macro_f1(y, ordi, classes), macro_f1(y, base, classes)
    boot = config["bootstrap"]
    interval = paired_bootstrap(y.to_numpy(), ordi.to_numpy(), base.to_numpy(),
                                valid["window_group"].to_numpy(), classes, boot["replicates"],
                                boot["level"], config["seed"])
    per_day = {}
    for day, rows in valid.groupby("day"):
        o = _day_metrics(rows["sensation_class"], rows["ordinal"], classes)
        b = _day_metrics(rows["sensation_class"], rows["baseline"], classes)
        per_day[day] = {"rows": len(rows), "ordinal": o, "baseline": b,
                        "delta_f1_macro": o["f1_macro"] - b["f1_macro"]}
    days = sorted(per_day)
    across_days = {
        name: _spread([per_day[d][name]["f1_macro"] for d in days])
        for name in ("ordinal", "baseline")
    }
    across_days["delta_f1_macro"] = _spread([per_day[d]["delta_f1_macro"] for d in days])
    out = table[~table["iso_valid"]]
    return {
        "comparison_rows": len(valid),
        "f1_macro_ordinal": f1_ord,
        "f1_macro_baseline": f1_base,
        "delta": f1_ord - f1_base,
        "delta_ci": interval,
        "by_day": per_day,
        "f1_macro_across_days": across_days,
        "ordinal": classification_metrics(y, ordi, classes),
        "baseline": classification_metrics(y, base, classes),
        "on_iso_out_of_range_rows": {
            "label": NO_COMPARISON,
            "ordinal": classification_metrics(out["sensation_class"], out["ordinal"], classes),
            "baseline": classification_metrics(out["sensation_class"], out["baseline"], classes),
        },
        **decide(f1_ord - f1_base, [per_day[d]["delta_f1_macro"] for d in days],
                 interval["low"]),
    }


def _load_baseline(table: pd.DataFrame, config: dict) -> pd.Series:
    """E-02 out-of-sample predictions, checked row by row against the final table."""
    e02 = pd.read_csv(E02_OOF_TABLE)
    for column in ("day", "window_group", "sensation_class", "iso_valid"):
        if not e02[column].equals(table[column]):
            raise ValueError(f"E-02 predictions do not align with the final table ({column})")
    valid = table["iso_valid"]
    f1 = macro_f1(table.loc[valid, "sensation_class"], e02.loc[valid, "ml_prediction"],
                  config["classes"])
    if not np.isclose(f1, BASELINE_F1, rtol=0, atol=1e-12):
        raise ValueError(f"E-02 baseline F1 {f1} differs from the reported {BASELINE_F1}")
    return e02["ml_prediction"]


def main() -> None:
    started = time.time()
    config = load_config(CONFIG_PATH)
    table = pd.read_csv(FINAL_TABLE)
    table["baseline"] = _load_baseline(table, config)
    predictions, folds = nested_cv(table, config, fit=ordinal_fit)
    table["ordinal"] = predictions
    table[["day", "window_group", "sensation_class", "ordinal", "baseline",
           "iso_valid"]].to_csv(OOF_TABLE, index=False, lineterminator="\n")

    report = compare_with_baseline(table, config)
    report["method"] = ("Frank & Hall ordinal decomposition over the preregistered combinations: "
                        "binary problems y > cool and y > neutral, monotone class probabilities, "
                        "argmax (ties to the lower class)")
    report["decision_rule"] = (f"candidate iff pooled delta > 0 and per-day delta > 0 on at least "
                               f"{MIN_DAYS_IMPROVED} of 5 days; improvement demonstrated only if "
                               f"the bootstrap interval low bound is also > 0")
    report["config_sha256"] = config_sha256(CONFIG_PATH)
    report["training_rows"] = len(table)
    report["outer_folds"] = [
        {
            "test_day": fold.day,
            "chosen": fold.selection.chosen.key,
            "best_by_mean": fold.selection.best.key,
            "best_mean_f1": fold.selection.best_mean,
            "best_se": fold.selection.best_se,
            "chosen_mean_f1": fold.selection.chosen_mean,
        }
        for fold in folds
    ]
    E04_REPORT.parent.mkdir(parents=True, exist_ok=True)
    E04_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                          encoding="utf-8", newline="\n")
    print(json.dumps({k: report[k] for k in ("f1_macro_ordinal", "f1_macro_baseline", "delta",
                                            "delta_ci", "days_improved", "decision",
                                            "improvement_demonstrated", "outer_folds")},
                     indent=2, ensure_ascii=False))
    print(f"elapsed {time.time() - started:.0f} s")


if __name__ == "__main__":
    main()
