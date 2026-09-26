"""P-08 to P-10: Nanjing cleaning rules and the E-01 reproduction of DATA_AUDIT.md."""

import json

import pytest

from gemetro.data.nanjing import (
    NANJING_ROOT,
    SENSATION_CLASS,
    mean_valid_speed,
    parse_window,
    repair_window,
    resolve_windows,
)
from gemetro.experiments.e01_nanjing_final_set import E01_REPORT


def _hm(text: str) -> tuple[int, int]:
    h, m = text.split(":")
    return int(h) * 60 + int(m)


# --- P-08: malformed windows ------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("11:24-11:5", ("11:24", "11:25")),  # truncated end
        ("24:25-14:26", ("14:25", "14:26")),  # invalid start hour
        ("16:27-16:18", ("16:27", "16:28")),  # end before start
        ("10:40-10:49", ("10:40", "10:41")),  # longer than 3 minutes
        ("12:7-12:48", ("12:07", "12:08")),  # start is a valid time
        ("15:00-15:91", ("15:00", "15:01")),  # invalid end minute
    ],
)
def test_malformed_windows_become_one_minute_from_the_valid_end(text, expected):
    start, end = repair_window(parse_window(text))
    assert (start, end) == (_hm(expected[0]), _hm(expected[1]))


def test_separator_typos_are_not_repairs():
    texts = ["9：52-9：53", "14；33-14:34", "10::18-10:19", "16:56:16:57", "9:06-9:08柳州东路"]
    windows, repaired = resolve_windows(texts)
    assert repaired == 0
    assert windows[3] == (_hm("16:56"), _hm("16:57"))


# --- P-09: other rules -----------------------------------------------------------------


def test_speeds_above_3_ms_are_discarded():
    assert mean_valid_speed(["0.4", "9.22", "0.6"]) == (pytest.approx(0.5), 1)
    assert mean_valid_speed(["11", "1.0", "2.0"]) == (pytest.approx(1.5), 1)


def test_seven_labels_map_to_three_classes():
    assert {k: SENSATION_CLASS[k] for k in ("很冷", "冷", "有点冷")} == dict.fromkeys(
        ("很冷", "冷", "有点冷"), "cool"
    )
    assert SENSATION_CLASS["中性"] == "neutral"
    assert {SENSATION_CLASS[k] for k in ("有点热", "热", "很热")} == {"warm"}


# --- P-10: E-01 counts as a regression test (DATA_AUDIT.md) ------------------------------

AUDIT_CLEAN_BY_DAY = {
    "2025-06-30": (14, 109, 36), "2025-07-03": (41, 110, 32), "2025-07-04": (32, 146, 21),
    "2025-07-06": (42, 116, 36), "2025-07-07": (23, 105, 19),
}
AUDIT_VALID_BY_DAY = {
    "2025-06-30": (5, 30, 4), "2025-07-03": (32, 94, 26), "2025-07-04": (28, 119, 17),
    "2025-07-06": (31, 80, 21), "2025-07-07": (18, 86, 17),
}


def _check_audit_counts(summary: dict) -> None:
    assert summary["clean_rows"] == 882
    assert summary["clean_classes"] == {"cool": 152, "neutral": 586, "warm": 144}
    for day, counts in AUDIT_CLEAN_BY_DAY.items():
        c = summary["clean_classes_by_day"][day]
        assert (c["cool"], c["neutral"], c["warm"]) == counts
    assert summary["clean_posture"] == {"seated": 613, "standing": 269}
    assert summary["clean_window_groups"] == {"groups": 854, "by_size": {"1": 826, "2": 28}}
    assert summary["iso_out_of_range"] == {
        "pa_gt_2700": 199, "ta_gt_30": 19, "vel_gt_1": 14, "any_input": 212,
        "pmv_below_minus_2": 62,
    }
    assert summary["iso_valid_rows"] == 608
    for day, counts in AUDIT_VALID_BY_DAY.items():
        c = summary["iso_valid_classes_by_day"][day]
        assert (c["cool"], c["neutral"], c["warm"]) == counts
    assert summary["iso_valid_window_groups"] == {"groups": 592, "by_size": {"1": 576, "2": 16}}
    assert summary["domain"] == {
        "ta": {"min": 21.07, "max": 31.63}, "rh": {"min": 52.05, "max": 89.47},
        "vel": {"min": 0.08, "max": 1.72}, "clo": {"min": 0.17, "max": 1.06},
    }


def test_versioned_e01_report_matches_audit():
    _check_audit_counts(json.loads(E01_REPORT.read_text(encoding="utf-8")))


@pytest.mark.skipif(not NANJING_ROOT.is_dir(), reason="raw Nanjing data not available")
def test_pipeline_reproduces_audit_from_raw_data():
    import pandas as pd

    from gemetro.data.nanjing import build_clean_table
    from gemetro.experiments.e01_nanjing_final_set import add_iso_flag, summarise

    clean, report = build_clean_table()
    # Same full-precision round trip as the pipeline's interim file.
    clean = pd.read_csv(pd.io.common.StringIO(clean.to_csv(index=False)))
    _check_audit_counts(summarise(add_iso_flag(clean)))
    totals = {k: sum(r[k] for r in report.values()) for k in next(iter(report.values()))}
    assert totals["annotation_rows"] == 38
    assert totals["data_rows"] == 894
    assert totals["windows_repaired"] == 13
    assert totals["speed_readings_discarded"] == 2
    assert (totals["excluded_no_logger_data"], totals["excluded_zero_speed"],
            totals["excluded_no_air_conditioning"]) == (3, 3, 6)
