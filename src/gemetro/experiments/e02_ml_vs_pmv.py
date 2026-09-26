"""E-02: ML vs PMV comparison (R-19), PHASE_1_ARCHITECTURE.md §8.2 points 1-9.

Input: data/interim/nanjing_final.csv (E-01) and the preregistered config/evaluation.toml.
Outputs:
- data/interim/e02_oof_predictions.csv: one out-of-sample prediction per clean row (local);
- reports/evaluation/e02_ml_vs_pmv.json: aggregated metrics, Δ with its interval, Δ per day,
  the combination chosen in every outer fold and the verdict (versioned).
"""

from __future__ import annotations

import json
import time

import pandas as pd

from gemetro.evaluation.candidates import CONFIG_PATH, config_sha256, load_config
from gemetro.evaluation.cv import nested_cv
from gemetro.evaluation.report import compare
from gemetro.experiments.e01_nanjing_final_set import FINAL_TABLE
from gemetro.paths import DATA_INTERIM, REPORTS

OOF_TABLE = DATA_INTERIM / "e02_oof_predictions.csv"
E02_REPORT = REPORTS / "evaluation" / "e02_ml_vs_pmv.json"


def main() -> None:
    started = time.time()
    config = load_config(CONFIG_PATH)
    table = pd.read_csv(FINAL_TABLE)
    predictions, folds = nested_cv(table, config)
    table["ml_prediction"] = predictions
    table[["day", "window_group", "sensation_class", "ml_prediction", "pmv_class",
           "iso_valid"]].to_csv(OOF_TABLE, index=False, lineterminator="\n")

    report = compare(table, config)
    report["config_sha256"] = config_sha256(CONFIG_PATH)
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
    E02_REPORT.parent.mkdir(parents=True, exist_ok=True)
    E02_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                          encoding="utf-8", newline="\n")
    print(json.dumps({k: report[k] for k in ("f1_macro_ml", "f1_macro_pmv", "delta", "delta_ci",
                                            "verdict", "outer_folds")}, indent=2,
                     ensure_ascii=False))
    print(f"elapsed {time.time() - started:.0f} s")


if __name__ == "__main__":
    main()
