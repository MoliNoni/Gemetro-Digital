"""E-05: derived thermal features vs the E-02 baseline (experimental; E-03 untouched).

Same protocol as E-02: the 882 clean rows, the preregistered grid and 1-SE rule, nested
leave-one-day-out (`nested_cv`) with each preregistered variant of
`gemetro.evaluation.features` injected as the `fit`. Paired comparison with E-02's
out-of-sample predictions on the same 608 ISO-valid rows. Decision rule
(odd/tasks/e05-thermal-features.md, fixed before running): screening with the E-04 rule
(`decide`), then a robustness rerun with two more seeds for the variants that pass.

Inputs: data/interim/nanjing_final.csv (E-01), data/interim/e02_oof_predictions.csv (E-02).
Outputs:
- data/interim/e05_oof_predictions.csv: out-of-sample predictions of every variant (local);
- reports/evaluation/e05_thermal_features.json: per-variant results and the decision (versioned).
"""

from __future__ import annotations

import json
import time

import pandas as pd

from gemetro.evaluation.candidates import CONFIG_PATH, config_sha256, load_config
from gemetro.evaluation.cv import macro_f1, nested_cv
from gemetro.evaluation.features import VARIANTS, variant_fit
from gemetro.evaluation.report import classification_metrics, paired_bootstrap
from gemetro.experiments.e01_nanjing_final_set import FINAL_TABLE
from gemetro.experiments.e04_ordinal import CANDIDATE, DISCARDED, _load_baseline, _spread, decide
from gemetro.paths import DATA_INTERIM, REPORTS

OOF_TABLE = DATA_INTERIM / "e05_oof_predictions.csv"
E05_REPORT = REPORTS / "evaluation" / "e05_thermal_features.json"
ROBUSTNESS_SEEDS = (20250926, 20250927)


def paired_by_day(valid: pd.DataFrame, variant: str, reference: str, classes) -> dict:
    """Pooled and per-day macro F1 of `variant` against `reference` on the same rows."""
    y = valid["sensation_class"]
    f1_v, f1_r = macro_f1(y, valid[variant], classes), macro_f1(y, valid[reference], classes)
    by_day = {}
    for day, rows in valid.groupby("day"):
        v = macro_f1(rows["sensation_class"], rows[variant], classes)
        r = macro_f1(rows["sensation_class"], rows[reference], classes)
        by_day[day] = {"rows": len(rows), "f1_macro": v, "f1_macro_reference": r,
                       "delta": v - r, "improves": bool(v > r)}
    days = sorted(by_day)
    return {
        "f1_macro": f1_v,
        "f1_macro_reference": f1_r,
        "delta": f1_v - f1_r,
        "by_day": by_day,
        "f1_macro_across_days": _spread([by_day[d]["f1_macro"] for d in days]),
        "delta_across_days": _spread([by_day[d]["delta"] for d in days]),
        "screening": decide(f1_v - f1_r, [by_day[d]["delta"] for d in days], 0.0)["decision"],
        "days_improved": sum(by_day[d]["improves"] for d in days),
    }


def _outer_folds(folds) -> list[dict]:
    return [{"test_day": f.day, "chosen": f.selection.chosen.key,
             "best_by_mean": f.selection.best.key, "chosen_mean_f1": f.selection.chosen_mean}
            for f in folds]


def main() -> None:
    started = time.time()
    config = load_config(CONFIG_PATH)
    classes = config["classes"]
    boot = config["bootstrap"]
    table = pd.read_csv(FINAL_TABLE)
    table["baseline"] = _load_baseline(table, config)
    valid_mask = table["iso_valid"]

    variants = {}
    for name, names in VARIANTS.items():
        predictions, folds = nested_cv(table, config, fit=variant_fit(names))
        table[name] = predictions
        valid = table[valid_mask]
        result = paired_by_day(valid, name, "baseline", classes)
        result["delta_ci"] = paired_bootstrap(
            valid["sensation_class"].to_numpy(), valid[name].to_numpy(),
            valid["baseline"].to_numpy(), valid["window_group"].to_numpy(), classes,
            boot["replicates"], boot["level"], config["seed"])
        result["added_features"] = list(names)
        result["metrics"] = classification_metrics(valid["sensation_class"], valid[name], classes)
        result["outer_folds"] = _outer_folds(folds)
        variants[name] = result
        print(f"{name}: F1 {result['f1_macro']:.4f} delta {result['delta']:+.4f} "
              f"days {result['days_improved']}/5 {result['screening']} "
              f"({time.time() - started:.0f} s)", flush=True)

    robustness = {}
    base_by_seed = {}
    for name, result in variants.items():
        if result["screening"] != CANDIDATE:
            continue
        robustness[name] = {}
        for seed in ROBUSTNESS_SEEDS:
            seeded = {**config, "seed": seed}
            if seed not in base_by_seed:
                base_by_seed[seed], _ = nested_cv(table, seeded)
            runs = pd.DataFrame({
                "day": table["day"], "sensation_class": table["sensation_class"],
                "variant": nested_cv(table, seeded, fit=variant_fit(VARIANTS[name]))[0],
                "base": base_by_seed[seed],
            })[valid_mask]
            check = paired_by_day(runs, "variant", "base", classes)
            robustness[name][str(seed)] = {k: check[k] for k in (
                "f1_macro", "f1_macro_reference", "delta", "days_improved", "screening")}
            print(f"  robustness {name} seed {seed}: delta {check['delta']:+.4f} "
                  f"days {check['days_improved']}/5 {check['screening']}", flush=True)

    for name, result in variants.items():
        robust = name in robustness and all(r["screening"] == CANDIDATE
                                            for r in robustness[name].values())
        result["decision"] = CANDIDATE if robust else DISCARDED
        result["improvement_demonstrated"] = bool(robust and result["delta_ci"]["low"] > 0)

    valid = table[valid_mask]
    baseline_days = {d: macro_f1(r["sensation_class"], r["baseline"], classes)
                     for d, r in valid.groupby("day")}
    report = {
        "comparison_rows": int(valid_mask.sum()),
        "training_rows": len(table),
        "baseline": {
            "f1_macro": macro_f1(valid["sensation_class"], valid["baseline"], classes),
            "f1_macro_by_day": baseline_days,
            "f1_macro_across_days": _spread([baseline_days[d] for d in sorted(baseline_days)]),
        },
        "variants": variants,
        "robustness": robustness,
        "candidates": [n for n, r in variants.items() if r["decision"] == CANDIDATE],
        "decision_rule": ("screening: pooled delta > 0 and per-day delta > 0 on at least 4 of 5 "
                          "days; candidate only if screening also holds against the base features "
                          f"with seeds {list(ROBUSTNESS_SEEDS)}; improvement demonstrated only if "
                          "the bootstrap interval low bound is also > 0"),
        "config_sha256": config_sha256(CONFIG_PATH),
        "seed": config["seed"],
    }
    table[["day", "window_group", "sensation_class", "iso_valid", "baseline",
           *VARIANTS]].to_csv(OOF_TABLE, index=False, lineterminator="\n")
    E05_REPORT.parent.mkdir(parents=True, exist_ok=True)
    E05_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                          encoding="utf-8", newline="\n")
    print(json.dumps({"candidates": report["candidates"], "robustness": robustness}, indent=2))
    print(f"elapsed {time.time() - started:.0f} s")


if __name__ == "__main__":
    main()
