"""I-11: comfort-model inference with its training-domain check.

Artifact contract (written by I-15, read here), in artifacts/comfort_model/:
- model.joblib: fitted scikit-learn estimator; `predict` takes a DataFrame with FEATURES
  and returns one of "cool" / "neutral" / "warm";
- domain.json: min-max of each numeric input over the final training rows, and postures;
- metadata.json: provenance of the model (I-15).

Domain rule (PHASE_0_REPORT.md; L-05): inclusive per-input min-max. Outside the domain the
class is still computed and returned with the extrapolation status. No class probability
is exposed (PHASE_1_ARCHITECTURE.md §3.1).

model.joblib is a pickle: only load artifacts produced by this repository's pipeline.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd

from gemetro.paths import ARTIFACTS

MODEL_DIR = ARTIFACTS / "comfort_model"
FEATURES = ["ta", "rh", "vel", "clo", "posture"]
NUMERIC_FEATURES = ["ta", "rh", "vel", "clo"]
CLASSES = ("cool", "neutral", "warm")

STATUS_IN_DOMAIN = "Dentro del dominio de entrenamiento"
STATUS_EXTRAPOLATION = "Extrapolación / fuera del dominio de entrenamiento"


@dataclass(frozen=True)
class ComfortPrediction:
    comfort_class: str
    domain_status: str
    out_of_domain: tuple[str, ...]  # inputs outside the training range


@dataclass(frozen=True)
class Domain:
    ranges: dict[str, tuple[float, float]]
    postures: tuple[str, ...]

    @classmethod
    def from_dict(cls, data: dict) -> Domain:
        ranges = {k: (float(data[k]["min"]), float(data[k]["max"])) for k in NUMERIC_FEATURES}
        return cls(ranges, tuple(data["postures"]))

    @classmethod
    def from_rows(cls, rows: pd.DataFrame) -> Domain:
        """Domain of the final training rows (min-max per input, I-15)."""
        ranges = {k: (float(rows[k].min()), float(rows[k].max())) for k in NUMERIC_FEATURES}
        return cls(ranges, tuple(sorted(rows["posture"].unique())))

    def to_dict(self) -> dict:
        data = {k: {"min": lo, "max": hi} for k, (lo, hi) in self.ranges.items()}
        data["postures"] = list(self.postures)
        return data

    def outside(self, inputs: dict[str, float | str]) -> tuple[str, ...]:
        out = tuple(
            k for k, (lo, hi) in self.ranges.items() if not lo <= float(inputs[k]) <= hi
        )
        if inputs["posture"] not in self.postures:
            out += ("posture",)
        return out


class ComfortModel:
    def __init__(self, estimator, domain: Domain):
        self._estimator = estimator
        self.domain = domain

    @classmethod
    def load(cls, directory: Path = MODEL_DIR) -> ComfortModel:
        if not (directory / "model.joblib").is_file():
            raise FileNotFoundError(
                f"no comfort model artifact in {directory}; it is produced by I-15"
            )
        domain = Domain.from_dict(json.loads((directory / "domain.json").read_text("utf-8")))
        return cls(joblib.load(directory / "model.joblib"), domain)

    def predict(self, ta: float, rh_percent: float, vel: float, clo: float,
                posture: str) -> ComfortPrediction:
        """Class for one condition. `rh_percent` in %, as in the training data."""
        inputs = {"ta": ta, "rh": rh_percent, "vel": vel, "clo": clo, "posture": posture}
        label = str(self._estimator.predict(pd.DataFrame([inputs], columns=FEATURES))[0])
        if label not in CLASSES:
            raise ValueError(f"model returned an unknown class {label!r}")
        out = self.domain.outside(inputs)
        status = STATUS_EXTRAPOLATION if out else STATUS_IN_DOMAIN
        return ComfortPrediction(label, status, out)


def save_artifact(estimator, domain: Domain, metadata: dict, directory: Path = MODEL_DIR) -> None:
    """Write the artifact contract (used by I-15 and by tests)."""
    directory.mkdir(parents=True, exist_ok=True)
    joblib.dump(estimator, directory / "model.joblib", compress=3)
    for name, data in (("domain.json", domain.to_dict()), ("metadata.json", metadata)):
        (directory / name).write_text(
            json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
