"""I-10: PMV baseline, ISO 7730 applied strictly (PHASE_0_REPORT.md, "Baseline PMV"; L-04, L-06).

- met is assigned from posture: seated 1.0, standing 1.2 (normative assignment).
- tr = ta (methodological assumption).
- The air speed is used as given (no relative-air-speed correction).
- If any input is outside the ISO 7730 validity ranges, or the resulting PMV is outside
  [-2, +2], the PMV is not reported: status "Fuera de rango para PMV". Nothing is clipped.
- Classes: PMV < -0.5 cool; -0.5 <= PMV <= +0.5 neutral; PMV > +0.5 warm.

This module is the single PMV implementation used by the evaluation and by the API.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

MET_BY_POSTURE = {"seated": 1.0, "standing": 1.2}

STATUS_VALID = "valid"
STATUS_OUT_OF_RANGE = "Fuera de rango para PMV"

# ISO 7730 validity ranges (DATA_SOURCES.md S-18), inclusive.
TA_RANGE = (10.0, 30.0)
TR_RANGE = (10.0, 40.0)
VEL_RANGE = (0.0, 1.0)
MET_RANGE = (0.8, 4.0)
CLO_RANGE = (0.0, 2.0)
PA_RANGE = (0.0, 2700.0)
PMV_RANGE = (-2.0, 2.0)
NEUTRAL_LIMIT = 0.5
# Keys match the `reasons` reported when the PMV is out of range (pa in Pa).
VALIDITY_RANGES = {"ta": TA_RANGE, "tr": TR_RANGE, "vel": VEL_RANGE, "met": MET_RANGE,
                   "clo": CLO_RANGE, "pa": PA_RANGE, "pmv": PMV_RANGE}


@dataclass(frozen=True)
class PmvResult:
    status: str  # STATUS_VALID or STATUS_OUT_OF_RANGE
    pmv: float | None
    pmv_class: str | None  # "cool" | "neutral" | "warm"
    reasons: tuple[str, ...]  # violated ranges when out of range


def vapour_pressure(ta: float, rh_percent: float) -> float:
    """Water vapour partial pressure in Pa, as defined in ISO 7730 (Annex D)."""
    return rh_percent * 10.0 * math.exp(16.6536 - 4030.183 / (ta + 235.0))


def fanger_pmv(ta: float, tr: float, vel: float, rh_percent: float, met: float, clo: float,
               wme: float = 0.0) -> float:
    """Fanger's PMV, following the ISO 7730 Annex D algorithm."""
    pa = vapour_pressure(ta, rh_percent)
    icl = 0.155 * clo
    m = met * 58.15
    w = wme * 58.15
    mw = m - w
    fcl = 1.0 + 1.29 * icl if icl <= 0.078 else 1.05 + 0.645 * icl
    hcf = 12.1 * math.sqrt(vel)
    taa = ta + 273.0
    tra = tr + 273.0
    tcla = taa + (35.5 - ta) / (3.5 * icl + 0.1)

    p1 = icl * fcl
    p2 = p1 * 3.96
    p3 = p1 * 100.0
    p4 = p1 * taa
    p5 = 308.7 - 0.028 * mw + p2 * (tra / 100.0) ** 4
    xn = tcla / 100.0
    xf = tcla / 50.0
    hc = hcf
    iterations = 0
    while abs(xn - xf) > 0.00015:
        xf = (xf + xn) / 2.0
        hcn = 2.38 * abs(100.0 * xf - taa) ** 0.25
        hc = max(hcf, hcn)
        xn = (p5 + p4 * hc - p2 * xf**4) / (100.0 + p3 * hc)
        iterations += 1
        if iterations > 150:
            raise ArithmeticError("PMV clothing temperature iteration did not converge")
    tcl = 100.0 * xn - 273.0

    hl1 = 3.05e-3 * (5733.0 - 6.99 * mw - pa)
    hl2 = 0.42 * (mw - 58.15) if mw > 58.15 else 0.0
    hl3 = 1.7e-5 * m * (5867.0 - pa)
    hl4 = 0.0014 * m * (34.0 - ta)
    hl5 = 3.96 * fcl * (xn**4 - (tra / 100.0) ** 4)
    hl6 = fcl * hc * (tcl - ta)
    ts = 0.303 * math.exp(-0.036 * m) + 0.028
    return ts * (mw - hl1 - hl2 - hl3 - hl4 - hl5 - hl6)


def classify(pmv: float) -> str:
    if pmv < -NEUTRAL_LIMIT:
        return "cool"
    if pmv > NEUTRAL_LIMIT:
        return "warm"
    return "neutral"


def _outside(value: float, bounds: tuple[float, float]) -> bool:
    return not bounds[0] <= value <= bounds[1]


def pmv_baseline(ta: float, rh_percent: float, vel: float, clo: float, posture: str) -> PmvResult:
    """Strict ISO 7730 PMV baseline for one condition.

    `rh_percent` is relative humidity in %, `ta` in °C, `vel` in m/s, `clo` in clo.
    """
    met = MET_BY_POSTURE[posture]
    tr = ta
    pa = vapour_pressure(ta, rh_percent)
    checks = {
        "ta": (ta, TA_RANGE),
        "tr": (tr, TR_RANGE),
        "vel": (vel, VEL_RANGE),
        "met": (met, MET_RANGE),
        "clo": (clo, CLO_RANGE),
        "pa": (pa, PA_RANGE),
    }
    reasons = tuple(name for name, (value, bounds) in checks.items() if _outside(value, bounds))
    if reasons:
        return PmvResult(STATUS_OUT_OF_RANGE, None, None, reasons)
    pmv = fanger_pmv(ta, tr, vel, rh_percent, met, clo)
    if _outside(pmv, PMV_RANGE):
        return PmvResult(STATUS_OUT_OF_RANGE, None, None, ("pmv",))
    return PmvResult(STATUS_VALID, pmv, classify(pmv), ())
