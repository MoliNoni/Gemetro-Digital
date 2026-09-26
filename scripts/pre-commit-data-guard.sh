#!/usr/bin/env bash
# P-01 data guard (PHASE_2_IMPLEMENTATION.md §5, I-22): refuses a commit that tracks raw data,
# images, spreadsheets or a copy of a raw file. Staged files are part of `git ls-files`.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
PYTHON=".venv/Scripts/python.exe"
[ -x "$PYTHON" ] || PYTHON=".venv/bin/python"
"$PYTHON" -m pytest -q -p no:cacheprovider tests/test_data_protection.py
