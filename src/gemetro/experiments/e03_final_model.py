"""I-15 / E-03: final model for the API (PHASE_1_ARCHITECTURE.md §8.2 point 10).

Runs the same `select` of I-13 over the five days (5 folds, L-09), without an outer loop,
refits the winning combination on the 882 clean rows and writes the artifact contract of
gemetro.comfort_model: model, domain (min-max of those same rows) and provenance metadata.
The combinations chosen in E-02's outer folds are not used (no voting, no averaging).
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from importlib.metadata import version

import pandas as pd

from gemetro.comfort_model import MODEL_DIR, Domain, save_artifact
from gemetro.evaluation.candidates import CONFIG_PATH, config_sha256, load_config
from gemetro.evaluation.cv import FEATURES, TARGET, _fit, select
from gemetro.experiments.e01_nanjing_final_set import FINAL_TABLE
from gemetro.paths import MANIFESTS, REPO_ROOT

LIBRARIES = ("numpy", "pandas", "scikit-learn", "joblib")


def _git_commit() -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True,
                            text=True, check=False)
    return result.stdout.strip() or "unknown"


def main() -> None:
    config = load_config(CONFIG_PATH)
    rows = pd.read_csv(FINAL_TABLE)
    days = sorted(rows["day"].unique())
    selection = select(rows, days, config)
    model = _fit(selection.chosen, config, rows)
    domain = Domain.from_rows(rows[FEATURES])
    metadata = {
        "chosen": selection.chosen.key,
        "best_by_mean": selection.best.key,
        "selection_mean_f1": selection.chosen_mean,
        "best_mean_f1": selection.best_mean,
        "best_se": selection.best_se,
        "training_rows": len(rows),
        "training_days": days,
        "target": TARGET,
        "features": FEATURES,
        "config_sha256": config_sha256(CONFIG_PATH),
        "nanjing_manifest_sha256": hashlib.sha256(
            (MANIFESTS / "nanjing.json").read_bytes()).hexdigest(),
        "code_commit": _git_commit(),
        "python": platform.python_version(),
        "libraries": {name: version(name) for name in LIBRARIES},
    }
    save_artifact(model, domain, metadata, MODEL_DIR)
    print(json.dumps({**metadata, "domain": domain.to_dict()}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
