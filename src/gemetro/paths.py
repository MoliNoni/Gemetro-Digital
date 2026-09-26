"""Repository-relative paths shared across the pipeline.

REPO_ROOT is resolved from this file's location: src/gemetro/paths.py has two
parents inside the src layout (gemetro/, src/), so parents[2] is the repo root.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

DATA_RAW = REPO_ROOT / "data" / "raw"
DATA_INTERIM = REPO_ROOT / "data" / "interim"
MANIFESTS = REPO_ROOT / "data" / "manifests"
ARTIFACTS = REPO_ROOT / "artifacts"
REPORTS = REPO_ROOT / "reports"
