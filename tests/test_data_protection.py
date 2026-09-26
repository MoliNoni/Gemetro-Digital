"""P-01: no raw data, image, spreadsheet or copy of a raw file is tracked by git.

Barrier 2 of PHASE_2_IMPLEMENTATION.md §5. Runs in the local suite; I-22 automates it
in a pre-commit hook and CI.
"""

import fnmatch
import hashlib
import shutil
import subprocess

import pytest

from gemetro.manifest import manifest_hashes
from gemetro.paths import MANIFESTS, REPO_ROOT

FORBIDDEN_PREFIXES = ("data/raw/", "data/interim/")
FORBIDDEN_PATTERNS = ("*.jpg", "*.jpeg", "*.xlsx")


def _tracked_files() -> list[str]:
    if shutil.which("git") is None:
        pytest.skip("git is not available")
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO_ROOT, capture_output=True, check=True
    ).stdout
    return [p for p in out.decode("utf-8").split("\0") if p]


def test_no_tracked_file_under_raw_or_interim():
    offending = [p for p in _tracked_files() if p.startswith(FORBIDDEN_PREFIXES)]
    assert offending == []


def test_no_tracked_image_or_spreadsheet():
    offending = [
        p
        for p in _tracked_files()
        if any(fnmatch.fnmatch(p.lower(), pattern) for pattern in FORBIDDEN_PATTERNS)
    ]
    assert offending == []


def test_no_tracked_copy_of_a_raw_file():
    raw_hashes = manifest_hashes(MANIFESTS)
    offending = []
    for rel in _tracked_files():
        path = REPO_ROOT / rel
        if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() in raw_hashes:
            offending.append(rel)
    assert offending == []


def _longest_list(value) -> int:
    if isinstance(value, dict):
        return max((_longest_list(v) for v in value.values()), default=0)
    if isinstance(value, list):
        return max([len(value), *(_longest_list(v) for v in value)])
    return 0


def test_versioned_outputs_hold_no_nanjing_rows():
    """P-02 (repository part): artifacts/ and reports/ contain aggregates only."""
    import json

    offending = []
    for folder in ("artifacts", "reports"):
        for path in (REPO_ROOT / folder).rglob("*"):
            if path.suffix == ".csv" and "sensation_class" in path.read_text(encoding="utf-8"):
                offending.append(path.name)
            # A row-level JSON dump would be a list with one entry per survey row (>= 100).
            if path.suffix == ".json" and _longest_list(
                json.loads(path.read_text(encoding="utf-8"))
            ) >= 100:
                offending.append(path.name)
    assert offending == []
