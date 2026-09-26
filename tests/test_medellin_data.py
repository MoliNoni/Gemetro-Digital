"""P-04 to P-07: Medellín climate and occupancy shape (I-05, I-06)."""

import pandas as pd
import pytest

from gemetro.data.climate import CLIMATE_ARTIFACT, hourly_median, to_local
from gemetro.data.occupancy_shape import (
    LINES,
    OCCUPANCY_ARTIFACT,
    OccupancyShapeError,
    line_shape,
)

SCENARIO_HOURS = list(range(4, 23))


# --- P-04: UTC -> UTC-5 and deduplication -------------------------------------------


def test_utc_to_local_crosses_midnight():
    local = to_local(pd.Series(["2025-03-10T03:00:00.000", "2025-01-01T05:00:00.000"]))
    assert local.tolist() == [pd.Timestamp("2025-03-09 22:00"), pd.Timestamp("2025-01-01 00:00")]


def test_hourly_median_drops_identical_duplicates_and_uses_local_hours():
    raw = pd.DataFrame(
        {
            # 13:00 and 13:30 UTC are 08:00 and 08:30 local; the 13:30 row appears 5 times.
            "fechaobservacion": ["2025-03-10T13:00:00"] + ["2025-03-10T13:30:00"] * 5,
            "valorobservado": ["20", "22", "22", "22", "22", "22"],
        }
    )
    table = hourly_median(raw)
    assert table.index.tolist() == [8]
    assert table.loc[8, "value"] == pytest.approx(21.0)
    assert table.loc[8, "days"] == 1


def test_hourly_median_is_median_over_days_of_hourly_means():
    raw = pd.DataFrame(
        {
            "fechaobservacion": [
                "2025-03-10T13:00:00", "2025-03-10T13:30:00",  # day 1 mean 21
                "2025-03-11T13:00:00",  # day 2 mean 30
                "2025-03-12T13:00:00",  # day 3 mean 18
            ],
            "valorobservado": ["20", "22", "30", "18"],
        }
    )
    assert hourly_median(raw).loc[8, "value"] == pytest.approx(21.0)


def test_rows_outside_local_year_are_excluded():
    # 2025-01-01 04:00 UTC is still 2024 in local time.
    raw = pd.DataFrame(
        {"fechaobservacion": ["2025-01-01T04:00:00"], "valorobservado": ["20"]}
    )
    assert hourly_median(raw).empty


# --- P-05: climate artifact ---------------------------------------------------------


@pytest.fixture(scope="module")
def climate():
    return pd.read_csv(CLIMATE_ARTIFACT).set_index("hour")


def test_climate_covers_scenario_hours(climate):
    rows = climate.loc[SCENARIO_HOURS]
    assert rows[["tout_c", "rh_out"]].notna().all().all()
    assert ((rows["rh_out"] > 0) & (rows["rh_out"] <= 1)).all()
    assert (rows[["days_tout", "days_rh"]] > 0).all().all()


# --- P-06 / P-07: occupancy shape ----------------------------------------------------

# PHASE_0_REPORT.md, "Forma temporal derivada: línea A, día hábil", and DATA_SOURCES.md S-15.
PHASE0_LINE_A = {
    4: (16743, 10, 7, 0.44), 5: (48701, 22, 15, 0.59), 6: (63478, 22, 23, 0.63),
    7: (55551, 23, 22, 0.55), 8: (33671, 16, 20, 0.42), 9: (27999, 12, 14, 0.48),
    10: (24484, 9, 10, 0.58), 11: (25808, 9, 10, 0.61), 12: (29835, 10, 9, 0.71),
    13: (28999, 9, 9, 0.72), 14: (34039, 11, 11, 0.70), 15: (38620, 12, 11, 0.75),
    16: (64518, 16, 13, 1.00), 17: (83272, 18, 22, 0.94), 18: (55323, 17, 23, 0.62),
    19: (31885, 13, 17, 0.48), 20: (21110, 8, 12, 0.47), 21: (16951, 7, 7, 0.54),
    22: (8518, 6, 7, 0.29),
}


@pytest.fixture(scope="module")
def shape():
    return pd.read_csv(OCCUPANCY_ARTIFACT)


def test_line_a_reproduces_phase0_table(shape):
    line_a = shape[shape["line"] == "A"].set_index("hour")
    assert line_a.index.tolist() == SCENARIO_HOURS
    for hour, (entries, dir0, dir1, ratio) in PHASE0_LINE_A.items():
        row = line_a.loc[hour]
        assert row["entries"] == entries
        assert (row["trains_dir0"], row["trains_dir1"]) == (dir0, dir1)
        assert round(row["load_ratio"], 2) == ratio
    assert line_a["load_ratio"].idxmax() == 16


def test_line_b_has_trains_and_a_single_peak(shape):
    line_b = shape[shape["line"] == "B"].set_index("hour")
    assert line_b.index.tolist() == SCENARIO_HOURS
    assert ((line_b["trains_dir0"] > 0) & (line_b["trains_dir1"] > 0)).all()
    assert (line_b["entries"] > 0).all()
    assert (line_b["load_ratio"] == 1.0).sum() == 1
    assert line_b["load_ratio"].between(0, 1).all()


def test_hour_without_trains_is_a_stop_point():
    entries = pd.Series({h: 100.0 for h in SCENARIO_HOURS})
    trains = pd.DataFrame({"0": {h: 5 for h in SCENARIO_HOURS}, "1": {h: 5 for h in SCENARIO_HOURS}})
    trains.loc[12, "1"] = 0
    with pytest.raises(OccupancyShapeError, match="without trains"):
        line_shape(entries, trains, LINES[1])
