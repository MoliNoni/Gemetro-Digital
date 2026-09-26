"""I-07: Nanjing survey loading and cleaning (DATA_AUDIT.md, "Nanjing: auditoría y limpieza final").

One canonical sheet per survey day plus the environmental logger of that day. Every rule
below is the closed audit rule; each exclusion is counted per rule and per day.

Output rows keep only the columns the ML and the PMV baseline need (data minimisation,
PHASE_2_IMPLEMENTATION.md §5). The row-level table is written to data/interim/ only.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import pandas as pd

from gemetro.manifest import verify_manifest
from gemetro.paths import DATA_INTERIM, DATA_RAW, MANIFESTS, REPORTS

NANJING_ROOT = DATA_RAW / "Data" / "Data"
CLEAN_TABLE = DATA_INTERIM / "nanjing_clean.csv"
CLEANING_REPORT = REPORTS / "nanjing_cleaning.json"


@dataclass(frozen=True)
class SurveyDay:
    day: str
    workbook: str
    sheet: str
    logger: str


SURVEY_DAYS = (
    SurveyDay("2025-06-30", "June 30/6月30号汇总.xlsx", "Sheet1", "June 30/2025630.csv"),
    SurveyDay("2025-07-03", "July 3/3号汇总.xlsx", "Sheet1", "July 3/202573.csv"),
    SurveyDay("2025-07-04", "July 4/4号汇总.xlsx", "Sheet2", "July 4/202574.csv"),
    SurveyDay("2025-07-06", "July 6/6号汇总.xlsx", "Sheet1", "July 6/202576.csv"),
    SurveyDay("2025-07-07", "July 7/7号汇总.xlsx", "Sheet1", "July 7/202577.csv"),
)

# Seven-point sensation labels grouped into three classes (text labels, not codes).
SENSATION_CLASS = {
    "很冷": "cool", "冷": "cool", "有点冷": "cool",
    "中性": "neutral",
    "有点热": "warm", "热": "warm", "很热": "warm",
}
POSTURE = {"静坐": "seated", "站立": "standing"}
NO_AIR_CONDITIONING = "无"
MAX_VALID_SPEED = 3.0  # m/s; faster readings are transcription errors (9.22 and 11 m/s)
MAX_WINDOW_MINUTES = 3

COL_WINDOW, COL_SPEED, COL_AC = "时间", "风速", "是否开空调"
COL_CLO, COL_POSTURE, COL_SENSATION = "穿衣状况", "活动状态", "车厢热感觉"

_TIME = r"(\d{1,2}):(\d{1,2})"
_WINDOW = re.compile(rf"^{_TIME}\s*[-:]\s*{_TIME}")


# --- Survey windows ----------------------------------------------------------------------


def _normalise_separators(text: str) -> str:
    return re.sub(r":+", ":", re.sub(r"[：；;]", ":", str(text).strip()))


def parse_window(text: str) -> tuple[int, int, int, int] | None:
    """(start_h, start_m, end_h, end_m) as typed, or None when unreadable."""
    match = _WINDOW.match(_normalise_separators(text))
    return tuple(int(g) for g in match.groups()) if match else None


def _minute(h: int, m: int) -> int | None:
    return h * 60 + m if 0 <= h <= 23 and 0 <= m <= 59 else None


def is_well_formed(parts: tuple[int, int, int, int]) -> bool:
    start, end = _minute(*parts[:2]), _minute(*parts[2:])
    return (
        start is not None
        and end is not None
        and start <= end
        and end - start <= MAX_WINDOW_MINUTES
    )


def repair_window(parts: tuple[int, int, int, int]) -> tuple[int, int]:
    """Rebuild a malformed window as a 1-minute window from its valid end.

    The start is the valid end when it is a valid time of day; otherwise the end is.
    Examples (DATA_AUDIT.md): "11:24-11:5" -> 11:24-11:25, "24:25-14:26" -> 14:25-14:26,
    "16:27-16:18" -> 16:27-16:28. Returns (start, end) in minutes of the day.
    """
    start, end = _minute(*parts[:2]), _minute(*parts[2:])
    if start is not None and start + 1 < 24 * 60:
        return start, start + 1
    if end is not None and end >= 1:
        return end - 1, end
    raise ValueError(f"window {parts} has no valid end")


def resolve_windows(texts: list[str]) -> tuple[list[tuple[int, int]], int]:
    """Windows in minutes of the day, in row order, and the number of repaired windows."""
    parsed = [parse_window(t) for t in texts]
    if any(p is None for p in parsed):
        unreadable = [t for t, p in zip(texts, parsed, strict=True) if p is None]
        raise ValueError(f"unreadable survey windows: {unreadable}")
    windows, repaired = [], 0
    for parts in parsed:
        if is_well_formed(parts):
            windows.append((_minute(*parts[:2]), _minute(*parts[2:])))
        else:
            windows.append(repair_window(parts))
            repaired += 1
    return windows, repaired


# --- Sheet and logger reading --------------------------------------------------------------


def read_survey_sheet(day: SurveyDay) -> tuple[pd.DataFrame, int]:
    """Data rows of a canonical sheet with the columns needed, in sheet order.

    The header row is located by its column names (on 2025-07-06 it is not the first row).
    A data row is a row whose sensation cell holds one of the seven labels; every other row
    is an annotation (line labels, outdoor temperatures, repeated headers, blank rows).
    """
    raw = pd.read_excel(NANJING_ROOT / day.workbook, sheet_name=day.sheet, header=None, dtype=str)
    is_header = raw.apply(lambda r: COL_WINDOW in r.values and COL_SENSATION in r.values, axis=1)
    header_row = raw.index[is_header][0]
    names = [str(v).strip() for v in raw.loc[header_row]]
    speed_first = names.index(COL_SPEED)
    body = raw.loc[header_row + 1 :].map(lambda v: v.strip() if isinstance(v, str) else v)
    sensation = body[names.index(COL_SENSATION)]
    data = body[sensation.isin(SENSATION_CLASS)]
    return pd.DataFrame(
        {
            "window_text": data[names.index(COL_WINDOW)],
            "speed_1": data[speed_first],
            "speed_2": data[speed_first + 1],
            "speed_3": data[speed_first + 2],
            "air_conditioning": data[names.index(COL_AC)],
            "clo": data[names.index(COL_CLO)],
            "posture_label": data[names.index(COL_POSTURE)],
            "sensation_label": data[names.index(COL_SENSATION)],
        }
    ).reset_index(drop=True), int(len(body) - len(data))


def read_logger(day: SurveyDay) -> pd.DataFrame:
    logger = pd.read_csv(NANJING_ROOT / day.logger, encoding_errors="replace")
    time = pd.to_datetime(logger["TIME"], format="%H:%M:%S")
    return pd.DataFrame(
        {
            "second": time.dt.hour * 3600 + time.dt.minute * 60 + time.dt.second,
            "ta": pd.to_numeric(logger["TEMPERATURE"]),
            "rh": pd.to_numeric(logger["HUMIDITY"]),
        }
    )


def window_means(logger: pd.DataFrame, start: int, end: int) -> tuple[float, float, int]:
    """Mean ta and rh of the logger from start:00 to end:59 (minutes of the day)."""
    inside = logger[(logger["second"] >= start * 60) & (logger["second"] <= end * 60 + 59)]
    return inside["ta"].mean(), inside["rh"].mean(), len(inside)


def mean_valid_speed(readings: list) -> tuple[float, int]:
    """Mean of the readings <= 3 m/s and the number of discarded readings."""
    values = [float(v) for v in readings if v is not None and not pd.isna(v)]
    kept = [v for v in values if v <= MAX_VALID_SPEED]
    return (sum(kept) / len(kept) if kept else float("nan")), len(values) - len(kept)


# --- Cleaning --------------------------------------------------------------------------------


def clean_day(day: SurveyDay) -> tuple[pd.DataFrame, dict]:
    sheet, annotation_rows = read_survey_sheet(day)
    logger = read_logger(day)
    windows, repaired = resolve_windows(sheet["window_text"].tolist())
    stats = {
        "annotation_rows": annotation_rows,
        "data_rows": len(sheet),
        "windows_repaired": repaired,
        "speed_readings_discarded": 0,
        "excluded_no_logger_data": 0,
        "excluded_zero_speed": 0,
        "excluded_no_air_conditioning": 0,
    }
    rows = []
    for record, (start, end) in zip(sheet.itertuples(), windows, strict=True):
        ta, rh, readings = window_means(logger, start, end)
        speeds = [record.speed_1, record.speed_2, record.speed_3]
        vel, discarded = mean_valid_speed(speeds)
        stats["speed_readings_discarded"] += discarded
        if readings == 0:
            stats["excluded_no_logger_data"] += 1
            continue
        if all(float(s) == 0 for s in speeds if s is not None and not pd.isna(s)):
            stats["excluded_zero_speed"] += 1
            continue
        if record.air_conditioning == NO_AIR_CONDITIONING:
            stats["excluded_no_air_conditioning"] += 1
            continue
        if record.posture_label not in POSTURE:
            raise ValueError(f"{day.day}: unexpected posture {record.posture_label!r}")
        rows.append(
            {
                "day": day.day,
                "window_start": f"{start // 60:02d}:{start % 60:02d}",
                "window_end": f"{end // 60:02d}:{end % 60:02d}",
                "ta": ta,
                "rh": rh,
                "vel": vel,
                "clo": float(record.clo),
                "posture": POSTURE[record.posture_label],
                "sensation_class": SENSATION_CLASS[record.sensation_label],
            }
        )
    stats["clean_rows"] = len(rows)
    return pd.DataFrame(rows), stats


def build_clean_table() -> tuple[pd.DataFrame, dict]:
    """Clean rows of the five days and the per-day cleaning statistics."""
    verify_manifest(MANIFESTS / "nanjing.json")
    tables, report = [], {}
    for day in SURVEY_DAYS:
        table, stats = clean_day(day)
        tables.append(table)
        report[day.day] = stats
    clean = pd.concat(tables, ignore_index=True)
    # Shared measurement window: same day and same logger window, hence the same ta and rh.
    keys = clean["day"] + " " + clean["window_start"] + "-" + clean["window_end"]
    clean.insert(3, "window_group", pd.factorize(keys)[0])
    return clean, report


def main() -> None:
    clean, report = build_clean_table()
    DATA_INTERIM.mkdir(parents=True, exist_ok=True)
    # Full precision: a lossy intermediate would move values across validity limits.
    clean.to_csv(CLEAN_TABLE, index=False, lineterminator="\n")
    totals = {k: sum(r[k] for r in report.values()) for k in next(iter(report.values()))}
    CLEANING_REPORT.parent.mkdir(parents=True, exist_ok=True)
    CLEANING_REPORT.write_text(
        json.dumps({"per_day": report, "total": totals}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(totals, indent=2))


if __name__ == "__main__":
    main()
