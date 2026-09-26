"""Manifests for raw data (PHASE_2_IMPLEMENTATION.md I-02).

A manifest records, for every file of interest under a root directory, its
relative path, size in bytes and SHA-256 digest. Files that are only counted
(never hashed, never read beyond a size check) are aggregated per suffix.
Manifests are written deterministically (sorted order, no timestamps) so two
runs over the same input produce byte-identical output (P-29).
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from gemetro.paths import DATA_RAW, MANIFESTS, REPO_ROOT

_HASH_CHUNK_SIZE = 1024 * 1024


class ManifestMismatchError(Exception):
    """Raised when a manifest does not match the files on disk."""


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(_HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(
    root: Path,
    include_suffixes: set[str],
    count_suffixes: set[str],
    base: Path = REPO_ROOT,
) -> dict:
    """Walk `root` and record hashed files plus per-suffix counts.

    `include_suffixes` and `count_suffixes` are lowercase file extensions
    (including the leading dot), e.g. {".xlsx", ".csv"}. Files whose suffix is
    in `include_suffixes` are hashed and listed. Files whose suffix is in
    `count_suffixes` are only counted (their size and content are never
    read). The two sets are expected to be disjoint. `root` is stored relative
    to `base` (the repository root by default).
    """
    root = root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"manifest root does not exist: {root}")
    files: list[dict] = []
    counted: dict[str, int] = {}

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in include_suffixes:
            files.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "size": path.stat().st_size,
                    "sha256": sha256_of(path),
                }
            )
        elif suffix in count_suffixes:
            counted[suffix] = counted.get(suffix, 0) + 1

    if not files:
        # Refuse to produce an empty manifest: on a clone without raw data this would
        # silently overwrite the versioned manifest.
        raise FileNotFoundError(f"no files to record under {root}")
    return {
        "root": root.relative_to(base.resolve()).as_posix(),
        "files": files,
        "counted": dict(sorted(counted.items())),
    }


def write_manifest(manifest: dict, path: Path) -> None:
    """Write `manifest` as deterministic, UTF-8, LF-terminated JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")


def verify_manifest(path: Path, base: Path = REPO_ROOT) -> None:
    """Re-hash every file listed in the manifest at `path`.

    Raises ManifestMismatchError naming every missing file and every file
    whose size or SHA-256 no longer matches the manifest.
    """
    manifest = json.loads(path.read_text(encoding="utf-8"))
    root = base / manifest["root"]

    problems: list[str] = []
    for entry in manifest["files"]:
        file_path = root / entry["path"]
        if not file_path.is_file():
            problems.append(f"missing file: {entry['path']}")
            continue
        actual_size = file_path.stat().st_size
        if actual_size != entry["size"]:
            problems.append(
                f"size mismatch for {entry['path']}: "
                f"expected {entry['size']}, got {actual_size}"
            )
            continue
        actual_sha256 = sha256_of(file_path)
        if actual_sha256 != entry["sha256"]:
            problems.append(
                f"sha256 mismatch for {entry['path']}: "
                f"expected {entry['sha256']}, got {actual_sha256}"
            )

    if problems:
        raise ManifestMismatchError("; ".join(problems))


def manifest_hashes(manifests_dir: Path) -> set[str]:
    """Return the set of every SHA-256 recorded across all manifests in `manifests_dir`."""
    hashes: set[str] = set()
    if not manifests_dir.is_dir():
        return hashes
    for manifest_path in sorted(manifests_dir.glob("*.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for entry in manifest.get("files", []):
            hashes.add(entry["sha256"])
    return hashes


def _build_nanjing_manifest() -> dict:
    root = DATA_RAW / "Data" / "Data"
    return build_manifest(
        root=root,
        include_suffixes={".xlsx", ".csv"},
        count_suffixes={".jpg", ".jpeg"},
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m gemetro.manifest")
    parser.add_argument("dataset", choices=["nanjing"])
    args = parser.parse_args()

    if args.dataset == "nanjing":
        manifest = _build_nanjing_manifest()
        output_path = MANIFESTS / "nanjing.json"
        write_manifest(manifest, output_path)
        counted = manifest["counted"]
        xlsx_count = sum(1 for f in manifest["files"] if f["path"].endswith(".xlsx"))
        csv_count = sum(1 for f in manifest["files"] if f["path"].endswith(".csv"))
        jpg_count = sum(counted.get(suffix, 0) for suffix in (".jpg", ".jpeg"))
        print(f"wrote {output_path}")
        print(f"xlsx={xlsx_count} csv={csv_count} jpg={jpg_count}")


if __name__ == "__main__":
    main()
