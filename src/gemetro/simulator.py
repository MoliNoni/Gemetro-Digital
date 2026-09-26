"""I-09: thermal and hygrometric simulator of the wagon, version 1.

Steady-state energy and moisture balance of a well-mixed wagon (PHASE_0_REPORT.md,
"Simulador térmico e higrométrico del vagón, versión 1"), equations 1-7 in that order.

Normal mode:   τr -> ΔT, W_in.
Advanced mode: ΔT fixed by the user -> W_in = W_out + ΔT·c_p·g/q_s, and the implied
               τr = ΔT·ρ_as·c_p·V/(N·q_s), reported as information.

This is the single simulator implementation used by the evaluation and by the API.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Fixed parameters (PHASE_0_REPORT.md, "Parámetros fijos"; PHASE_1_ARCHITECTURE.md §9.2).
P_HPA = 851.0  # atmospheric pressure, IDEAM Olaya Herrera 2025
VOLUME_M3 = 150.0  # wagon volume (assumption, S-14)
Q_SENSIBLE_W = 70.0  # sensible heat per passenger (reference, S-12)
G_KG_S = 70.0 / 1000.0 / 3600.0  # moisture per passenger: 70 g/h in kg/s (reference, S-12)
CP_DRY_AIR = 1006.0  # J/(kg·K)
R_DRY_AIR = 287.055  # J/(kg·K)
MAGNUS_MAX_C = 50.0  # validity limit of the Magnus formula over water

STATUS_OUTSIDE_SIMULATOR_VALIDITY = "fuera de validez del simulador"


@dataclass(frozen=True)
class SimulationResult:
    tin: float  # °C
    rh_in: float  # fraction 0-1
    delta_t: float  # K
    w_out: float  # kg/kg
    w_in: float  # kg/kg
    rho_dry_air: float  # kg/m³, at the inlet (outdoor) conditions
    mass_flow: float | None  # kg/s of dry air; None in advanced mode
    tau_r: float | None  # s; input in normal mode, implied in advanced mode
    rh_limited: bool  # RH_in reached 1 and was limited (protection flag)
    outside_validity: bool  # Tin above the Magnus validity limit

    @property
    def status(self) -> str | None:
        return STATUS_OUTSIDE_SIMULATOR_VALIDITY if self.outside_validity else None


def saturation_pressure_hpa(t_c: float) -> float:
    """Equation 1 — Magnus (WMO), over water, valid 0-50 °C."""
    return 6.112 * math.exp(17.62 * t_c / (243.12 + t_c))


def humidity_ratio(rh: float, t_c: float, p_hpa: float = P_HPA) -> float:
    """Equation 2 — W = 0.622·RH·e_s / (p − RH·e_s), kg/kg."""
    e = rh * saturation_pressure_hpa(t_c)
    return 0.622 * e / (p_hpa - e)


def dry_air_density(t_c: float, rh: float, p_hpa: float = P_HPA) -> float:
    """Equation 3 — ρ_as = (p − RH·e_s)·100 / (R_as·(T + 273.15)), kg/m³."""
    e = rh * saturation_pressure_hpa(t_c)
    return (p_hpa - e) * 100.0 / (R_DRY_AIR * (t_c + 273.15))


def relative_humidity(w: float, t_c: float, p_hpa: float = P_HPA) -> float:
    """Equation 7 — RH = W·p / ((0.622 + W)·e_s(T)), fraction."""
    return w * p_hpa / ((0.622 + w) * saturation_pressure_hpa(t_c))


def _finish(tout: float, rh_out: float, delta_t: float, w_in: float, rho: float,
            mass_flow: float | None, tau_r: float | None) -> SimulationResult:
    tin = tout + delta_t
    rh_in = relative_humidity(w_in, tin)
    rh_limited = rh_in >= 1.0
    return SimulationResult(
        tin=tin,
        rh_in=min(rh_in, 1.0),
        delta_t=delta_t,
        w_out=humidity_ratio(rh_out, tout),
        w_in=w_in,
        rho_dry_air=rho,
        mass_flow=mass_flow,
        tau_r=tau_r,
        rh_limited=rh_limited,
        outside_validity=tin > MAGNUS_MAX_C,
    )


def simulate(tout: float, rh_out: float, n: float, tau_r: float) -> SimulationResult:
    """Normal mode: indoor conditions from occupancy `n` and renewal time constant `tau_r` (s).

    `rh_out` is a fraction (0-1).
    """
    if tau_r <= 0:
        raise ValueError("tau_r must be positive")
    rho = dry_air_density(tout, rh_out)
    mass_flow = rho * VOLUME_M3 / tau_r  # equation 4, one flow for both balances
    delta_t = n * Q_SENSIBLE_W / (mass_flow * CP_DRY_AIR)  # equation 5
    w_in = humidity_ratio(rh_out, tout) + n * G_KG_S / mass_flow  # equation 6
    return _finish(tout, rh_out, delta_t, w_in, rho, mass_flow, tau_r)


def simulate_advanced(tout: float, rh_out: float, n: float, delta_t: float) -> SimulationResult:
    """Advanced mode: ΔT fixed by the user ("supuesto del usuario")."""
    if delta_t < 0:
        raise ValueError("delta_t must not be negative")
    rho = dry_air_density(tout, rh_out)
    w_in = humidity_ratio(rh_out, tout) + delta_t * CP_DRY_AIR * G_KG_S / Q_SENSIBLE_W
    implied_tau = (
        delta_t * rho * CP_DRY_AIR * VOLUME_M3 / (n * Q_SENSIBLE_W) if n > 0 else None
    )
    return _finish(tout, rh_out, delta_t, w_in, rho, None, implied_tau)
