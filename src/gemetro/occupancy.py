"""I-08: simulated wagon occupancy N(h) = min(1, φ_pico · I(h)/I_pico) · C_vagón.

The shape I(h)/I_pico is read from artifacts/occupancy_shape.csv (I-06). φ_pico is a
scenario assumption and C_vagón a reference value; N is derived/simulated, not a count.
"""

from __future__ import annotations

from functools import lru_cache

import pandas as pd

from gemetro.data.occupancy_shape import OCCUPANCY_ARTIFACT

C_WAGON = 300  # reference capacity per wagon (S-16)


@lru_cache(maxsize=1)
def load_shape() -> dict[tuple[str, int], float]:
    table = pd.read_csv(OCCUPANCY_ARTIFACT)
    return {(r.line, int(r.hour)): float(r.load_ratio) for r in table.itertuples()}


def load_ratio(line: str, hour: int) -> float:
    """I(h)/I_pico for a line and a scenario hour."""
    try:
        return load_shape()[(line, hour)]
    except KeyError:
        raise ValueError(f"no occupancy shape for line {line!r} at hour {hour}") from None


def occupancy_fraction(ratio: float, phi_peak: float) -> float:
    """φ(h) = min(1, φ_pico · I(h)/I_pico)."""
    return min(1.0, phi_peak * ratio)


def occupancy(line: str, hour: int, phi_peak: float, c_wagon: float = C_WAGON) -> float:
    """N(h): passengers in the wagon for the scenario (never above C_vagón)."""
    return occupancy_fraction(load_ratio(line, hour), phi_peak) * c_wagon
