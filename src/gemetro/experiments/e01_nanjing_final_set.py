"""E-01: reproduce the final Nanjing set of DATA_AUDIT.md with the definitive code.

Runs I-07 (cleaning) and I-10 (strict ISO 7730 PMV) and writes:
- data/interim/nanjing_final.csv: clean rows plus the ISO validity flag (local only);
- reports/e01_nanjing_final_set.json: aggregated counts (versioned, no row-level data).

The ISO flag depends only on the row, so it is fixed before any model is trained
(PHASE_1_ARCHITECTURE.md §8.2, point 1).
"""

from __future__ import annotations

import json

import pandas as pd

from gemetro.data.nanjing import CLEAN_TABLE
from gemetro.data.nanjing import main as run_cleaning
from gemetro.paths import DATA_INTERIM, REPORTS
from gemetro.pmv import STATUS_VALID, pmv_baseline, vapour_pressure

FINAL_TABLE = DATA_INTERIM / "nanjing_final.csv"
E01_REPORT = REPORTS / "e01_nanjing_final_set.json"
CLASSES = ["cool", "neutral", "warm"]


def add_iso_flag(clean: pd.DataFrame) -> pd.DataFrame:
    results = [
        pmv_baseline(r.ta, r.rh, r.vel, r.clo, r.posture) for r in clean.itertuples()
    ]
    table = clean.copy()
    table["pa"] = [vapour_pressure(r.ta, r.rh) for r in clean.itertuples()]
    table["pmv"] = [r.pmv for r in results]
    table["pmv_class"] = [r.pmv_class for r in results]
    table["iso_valid"] = [r.status == STATUS_VALID for r in results]
    table["iso_reasons"] = ["+".join(r.reasons) for r in results]
    return table


def _classes_by_day(table: pd.DataFrame) -> dict:
    counts = pd.crosstab(table["day"], table["sensation_class"]).reindex(
        columns=CLASSES, fill_value=0
    )
    return {day: row.to_dict() for day, row in counts.iterrows()}


def _group_sizes(table: pd.DataFrame) -> dict:
    sizes = table.groupby("window_group").size().value_counts().sort_index()
    return {"groups": int(table["window_group"].nunique()),
            "by_size": {str(k): int(v) for k, v in sizes.items()}}


def summarise(table: pd.DataFrame) -> dict:
    inputs_out = table["iso_reasons"].str.len() > 0
    pmv_out = table["iso_reasons"] == "pmv"
    valid = table[table["iso_valid"]]
    return {
        "clean_rows": len(table),
        "clean_classes": table["sensation_class"].value_counts().reindex(CLASSES).to_dict(),
        "clean_classes_by_day": _classes_by_day(table),
        "clean_posture": table["posture"].value_counts().to_dict(),
        "clean_window_groups": _group_sizes(table),
        "domain": {
            col: {"min": round(float(table[col].min()), 2), "max": round(float(table[col].max()), 2)}
            for col in ["ta", "rh", "vel", "clo"]
        },
        "iso_out_of_range": {
            "pa_gt_2700": int((table["pa"] > 2700).sum()),
            "ta_gt_30": int((table["ta"] > 30).sum()),
            "vel_gt_1": int((table["vel"] > 1).sum()),
            "any_input": int((inputs_out & ~pmv_out).sum()),
            "pmv_below_minus_2": int(pmv_out.sum()),
        },
        "iso_valid_rows": len(valid),
        "iso_valid_classes_by_day": _classes_by_day(valid),
        "iso_valid_window_groups": _group_sizes(valid),
    }


def main() -> None:
    run_cleaning()
    table = add_iso_flag(pd.read_csv(CLEAN_TABLE))
    table.to_csv(FINAL_TABLE, index=False, lineterminator="\n")
    summary = summarise(table)
    E01_REPORT.write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
