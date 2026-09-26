"""E-06: ASHRAE-augmented training vs the E-02 baseline (experimental; official model and
E-03 (`artifacts/comfort_model/`) untouched).

Same protocol as E-02: the 882 Nanjing rows of data/interim/nanjing_final.csv, the
preregistered config/evaluation.toml grid and 1-SE rule, nested leave-one-day-out
(`nested_cv`), with every inner and outer fit augmented by in-domain ASHRAE rows
(`gemetro.evaluation.augment.augmented_fit`). ASHRAE rows enter training only; validation and
test rows are always Nanjing, and no ASHRAE row ever crosses a CV split. Comparison paired
with E-02's out-of-sample predictions on the same 608 ISO-valid rows. Screening decision
(odd/tasks/e06-ashrae-augmentation.md, fixed before running): the E-04 rule (`decide`) --
pooled delta > 0 and per-day delta > 0 on at least 4 of 5 days. Robustness reruns and the
publication/licence decision are out of scope for this script (see the task tracker).

Inputs: data/interim/nanjing_final.csv (E-01), data/interim/e02_oof_predictions.csv (E-02),
the ASHRAE Global Thermal Comfort Database II (data/raw/ashrae-db-II-master/...; reference
data, AGENTS.md §4).
Outputs:
- data/interim/e06_oof_predictions.csv: one out-of-sample E-06 prediction per row (local);
- reports/evaluation/e06_ashrae_augmentation.json: metrics, per-day and per-class results,
  ASHRAE eligibility counts and the screening decision (versioned).
"""

from __future__ import annotations

import json
import time

import pandas as pd

from gemetro.data.ashrae import load_ashrae
from gemetro.evaluation.augment import augmented_fit, domain_filter
from gemetro.evaluation.candidates import CONFIG_PATH, config_sha256, load_config
from gemetro.evaluation.cv import nested_cv
from gemetro.evaluation.report import classification_metrics, paired_bootstrap
from gemetro.experiments.e01_nanjing_final_set import FINAL_TABLE
from gemetro.experiments.e04_ordinal import _load_baseline
from gemetro.experiments.e05_thermal_features import paired_by_day
from gemetro.paths import DATA_INTERIM, REPORTS

OOF_TABLE = DATA_INTERIM / "e06_oof_predictions.csv"
E06_REPORT = REPORTS / "evaluation" / "e06_ashrae_augmentation.json"


def _ashrae_class_counts(ashrae: pd.DataFrame, classes: list[str]) -> dict:
    counts = ashrae["sensation_class"].value_counts()
    return {c: int(counts.get(c, 0)) for c in classes}


def _outer_folds(table: pd.DataFrame, ashrae: pd.DataFrame, folds) -> list[dict]:
    """Chosen combination per outer fold plus the ASHRAE rows used in its outer refit.

    `domain_filter` is recomputed here on each fold's outer training rows (`nested_cv`'s own
    `train`, before the winning combination is refit on it) -- a pure, independent check of
    what `augmented_fit` used, without altering `nested_cv` itself.
    """
    days = sorted(table["day"].unique())
    out = []
    for fold in folds:
        training_days = [d for d in days if d != fold.day]
        train = table[table["day"].isin(training_days)]
        out.append({
            "test_day": fold.day,
            "chosen": fold.selection.chosen.key,
            "best_by_mean": fold.selection.best.key,
            "best_mean_f1": fold.selection.best_mean,
            "best_se": fold.selection.best_se,
            "chosen_mean_f1": fold.selection.chosen_mean,
            "ashrae_rows_outer_refit": len(domain_filter(ashrae, train)),
        })
    return out


def main() -> None:
    started = time.time()
    config = load_config(CONFIG_PATH)
    classes = config["classes"]
    boot = config["bootstrap"]
    table = pd.read_csv(FINAL_TABLE)
    table["baseline"] = _load_baseline(table, config)
    ashrae = load_ashrae()

    predictions, folds = nested_cv(table, config, fit=augmented_fit(ashrae))
    table["e06"] = predictions
    table[["day", "window_group", "sensation_class", "e06", "baseline",
           "iso_valid"]].to_csv(OOF_TABLE, index=False, lineterminator="\n")

    valid = table[table["iso_valid"]]
    result = paired_by_day(valid, "e06", "baseline", classes)
    result["delta_ci"] = paired_bootstrap(
        valid["sensation_class"].to_numpy(), valid["e06"].to_numpy(),
        valid["baseline"].to_numpy(), valid["window_group"].to_numpy(), classes,
        boot["replicates"], boot["level"], config["seed"])
    result["metrics"] = classification_metrics(valid["sensation_class"], valid["e06"], classes)
    result["baseline_metrics"] = classification_metrics(valid["sensation_class"],
                                                         valid["baseline"], classes)
    result["outer_folds"] = _outer_folds(table, ashrae, folds)

    report = {
        "comparison_rows": len(valid),
        "training_rows": len(table),
        "ashrae": {
            "eligible_rows": len(ashrae),
            "eligible_by_class": _ashrae_class_counts(ashrae, classes),
        },
        "result": result,
        "decision": result["screening"],
        "decision_rule": ("screening (E-04 rule): pooled delta > 0 and per-day delta > 0 on "
                          "at least 4 of 5 days; robustness reruns and the publication/licence "
                          "decision are out of scope for this script"),
        "config_sha256": config_sha256(CONFIG_PATH),
        "seed": config["seed"],
    }
    E06_REPORT.parent.mkdir(parents=True, exist_ok=True)
    E06_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                          encoding="utf-8", newline="\n")
    print(json.dumps({"decision": report["decision"], "delta": result["delta"],
                      "delta_ci": result["delta_ci"], "days_improved": result["days_improved"]},
                     indent=2, ensure_ascii=False))
    print(f"elapsed {time.time() - started:.0f} s")


if __name__ == "__main__":
    main()
