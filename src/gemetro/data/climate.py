"""I-05: outdoor climate table for the "typical 2025 weekday" scenario (L-01, L-11).

Method, per variable and independently:
1. drop identical duplicate rows (R-07);
2. convert the UTC timestamp to local time (UTC-5, Colombia has no daylight saving);
3. keep local year 2025 and average every (local date, local hour);
4. take, for each local hour, the median of those hourly means over the days with data.

No outlier filter is applied: none is defined by the closed decisions.
"""

from __future__ import annotations

import pandas as pd

from gemetro.data.medellin_download import MEDELLIN_RAW
from gemetro.paths import ARTIFACTS

LOCAL_UTC_OFFSET = pd.Timedelta(hours=-5)
CLIMATE_ARTIFACT = ARTIFACTS / "climate_hourly_2025.csv"

TEMPERATURE_FILE = "ideam_temperature_0071_2025.csv"
HUMIDITY_FILE = "ideam_humidity_0028_2025.csv"


def to_local(utc_timestamps: pd.Series) -> pd.Series:
    """Convert naive UTC timestamps (IDEAM `fechaobservacion`) to naive local time."""
    return pd.to_datetime(utc_timestamps) + LOCAL_UTC_OFFSET


def hourly_median(raw: pd.DataFrame, year: int = 2025) -> pd.DataFrame:
    """Median over days of the hourly means, per local hour.

    `raw` has the IDEAM columns `fechaobservacion` (UTC) and `valorobservado`.
    Returns a frame indexed by local hour with columns `value` and `days`.
    """
    data = raw[["fechaobservacion", "valorobservado"]].drop_duplicates()
    local = to_local(data["fechaobservacion"])
    values = pd.to_numeric(data["valorobservado"])
    in_year = local.dt.year == year
    local, values = local[in_year], values[in_year]
    hourly_means = values.groupby([local.dt.date, local.dt.hour]).mean()
    by_hour = hourly_means.groupby(level=1)
    result = pd.DataFrame({"value": by_hour.median(), "days": by_hour.size()})
    result.index.name = "hour"
    return result


def build_climate_table() -> pd.DataFrame:
    temperature = hourly_median(pd.read_csv(MEDELLIN_RAW / TEMPERATURE_FILE, dtype=str))
    humidity = hourly_median(pd.read_csv(MEDELLIN_RAW / HUMIDITY_FILE, dtype=str))
    table = pd.DataFrame(
        {
            "tout_c": temperature["value"],
            "rh_out": humidity["value"] / 100.0,
            "days_tout": temperature["days"],
            "days_rh": humidity["days"],
        }
    )
    return table.reset_index()


def main() -> None:
    table = build_climate_table()
    CLIMATE_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(CLIMATE_ARTIFACT, index=False, float_format="%.4f", lineterminator="\n")
    print(f"wrote {CLIMATE_ARTIFACT} ({len(table)} hours)")


if __name__ == "__main__":
    main()
