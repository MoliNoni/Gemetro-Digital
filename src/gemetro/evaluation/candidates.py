"""Preregistered candidate models (I-12 config -> estimators).

Each combination is one candidate x hyperparameters x class weight, expanded in the order
of config/evaluation.toml; that order breaks exact ties deterministically.
"""

from __future__ import annotations

import hashlib
import itertools
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

from gemetro.paths import REPO_ROOT

CONFIG_PATH = REPO_ROOT / "config" / "evaluation.toml"
NUMERIC = ["ta", "rh", "vel", "clo"]
LOGISTIC = "logistic_regression"


@dataclass(frozen=True)
class Combination:
    candidate: str
    params: dict = field(hash=False)
    class_weight: str  # "none" | "balanced"

    @property
    def key(self) -> str:
        params = ", ".join(f"{k}={v}" for k, v in self.params.items())
        return f"{self.candidate}({params}, class_weight={self.class_weight})"


def load_config(path: Path = CONFIG_PATH) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def config_sha256(path: Path = CONFIG_PATH) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _none(value):
    return None if value == "none" else value


def combinations(config: dict) -> list[Combination]:
    spec = config["candidates"]
    weights = config["class_weight"]
    result = []
    lr = spec["logistic_regression"]
    for c, w in itertools.product(lr["C"], weights):
        result.append(Combination(LOGISTIC, {"C": c}, w))
    rf = spec["random_forest"]
    for depth, leaf, w in itertools.product(rf["max_depth"], rf["min_samples_leaf"], weights):
        result.append(Combination("random_forest",
                                  {"max_depth": _none(depth), "min_samples_leaf": leaf}, w))
    gb = spec["gradient_boosting"]
    for rate, depth, iters, w in itertools.product(
        gb["learning_rate"], gb["max_depth"], gb["max_iter"], weights
    ):
        result.append(Combination("gradient_boosting",
                                  {"learning_rate": rate, "max_depth": depth, "max_iter": iters}, w))
    return result


def build_estimator(combination: Combination, config: dict) -> Pipeline:
    """Unfitted pipeline for one combination; preprocessing is fitted inside each fold."""
    seed = config["seed"]
    weight = _none(combination.class_weight)
    spec = config["candidates"][combination.candidate]
    if combination.candidate == LOGISTIC:
        encode = ColumnTransformer(
            [("numeric", StandardScaler(), NUMERIC),
             ("posture", OneHotEncoder(drop="first"), ["posture"])]
        )
        model = LogisticRegression(C=combination.params["C"], class_weight=weight,
                                   max_iter=spec["max_iter"])
    else:
        encode = ColumnTransformer(
            [("numeric", "passthrough", NUMERIC),
             ("posture", OrdinalEncoder(categories=[["seated", "standing"]]), ["posture"])]
        )
        if combination.candidate == "random_forest":
            model = RandomForestClassifier(
                n_estimators=spec["n_estimators"], class_weight=weight, random_state=seed,
                n_jobs=-1, **combination.params,
            )
        else:
            model = HistGradientBoostingClassifier(
                class_weight=weight, random_state=seed, early_stopping=spec["early_stopping"],
                **combination.params,
            )
    return Pipeline([("encode", encode), ("model", model)])
