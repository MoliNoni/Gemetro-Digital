"""E-06: ASHRAE Global Thermal Comfort Database II loading (reference data, not Nanjing).

Data category (AGENTS.md §4): these are building surveys from the ASHRAE Global Thermal
Comfort Database II, not Nanjing metro-car rows. They are used only as reference data to
augment training in E-06 (odd/tasks/e06-ashrae-augmentation.md); they never enter validation
or the official model's domain. ASHRAE records no posture, so every eligible row carries the
explicit category "unknown" -- a missing-data marker, never a value imputed from `met` or any
other column.

Eligibility (fixed before running E-06):
1. `thermal_sensation` integer-valued (continuous-scale votes excluded).
2. `ta`, `rh`, `vel`, `clo`, `thermal_sensation` all present.
3. Building `quality_assurance == "pass"`.
4. Class: `< 0` cool, `0` neutral, `> 0` warm (same grouping as Nanjing's 7-point labels).

Step 5 of the design (inside the Nanjing training domain of one fit call) is applied later,
per fit, by `gemetro.evaluation.augment.domain_filter` -- never here, since it depends on the
fold's training rows.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from gemetro.paths import DATA_RAW

ASHRAE_ROOT = DATA_RAW / "ashrae-db-II-master" / "ashrae-db-II-master" / "v2.1.0"
MEASUREMENTS = ASHRAE_ROOT / "db_measurements_v2.1.0.csv.gz"
METADATA = ASHRAE_ROOT / "db_metadata.csv"

POSTURE_UNKNOWN = "unknown"
QA_PASS = "pass"
REQUIRED = ["ta", "rh", "vel", "clo", "thermal_sensation"]


def _sensation_class(thermal_sensation: pd.Series) -> pd.Series:
    return pd.Series(
        np.where(thermal_sensation < 0, "cool", np.where(thermal_sensation > 0, "warm", "neutral")),
        index=thermal_sensation.index,
    )


def load_ashrae(measurements_path: Path = MEASUREMENTS,
                metadata_path: Path = METADATA) -> pd.DataFrame:
    """Eligible ASHRAE rows with columns `ta, rh, vel, clo, posture, sensation_class`.

    `posture` is always `"unknown"`: ASHRAE records no posture, and it is never derived from
    `met` or any other column (odd/tasks/e06-ashrae-augmentation.md).
    """
    measurements = pd.read_csv(
        measurements_path, compression="gzip",
        usecols=["building_id", *REQUIRED],
    )
    metadata = pd.read_csv(metadata_path, usecols=["building_id", "quality_assurance"])
    merged = measurements.merge(metadata, on="building_id", how="left")

    complete = merged[REQUIRED].notna().all(axis=1)
    integer_valued = np.isclose(merged["thermal_sensation"], merged["thermal_sensation"].round())
    qa_pass = merged["quality_assurance"] == QA_PASS
    eligible = merged[complete & integer_valued & qa_pass].copy()

    eligible["posture"] = POSTURE_UNKNOWN
    eligible["sensation_class"] = _sensation_class(eligible["thermal_sensation"])
    return eligible[["ta", "rh", "vel", "clo", "posture", "sensation_class"]].reset_index(drop=True)
