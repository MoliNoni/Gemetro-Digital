"""P-03: the pipeline stops when a raw file no longer matches its manifest."""

import pytest

from gemetro.manifest import (
    ManifestMismatchError,
    build_manifest,
    manifest_hashes,
    verify_manifest,
    write_manifest,
)


@pytest.fixture
def raw_tree(tmp_path):
    root = tmp_path / "raw"
    (root / "day1").mkdir(parents=True)
    (root / "day1" / "survey.xlsx").write_bytes(b"xlsx-bytes")
    (root / "day1" / "logger.csv").write_bytes(b"a,b\n1,2\n")
    (root / "day1" / "photo.jpg").write_bytes(b"image-bytes")
    return tmp_path, root


def _manifest(base, root):
    return build_manifest(root, {".xlsx", ".csv"}, {".jpg", ".jpeg"}, base=base)


def test_images_are_counted_not_listed(raw_tree):
    base, root = raw_tree
    manifest = _manifest(base, root)
    assert [f["path"] for f in manifest["files"]] == ["day1/logger.csv", "day1/survey.xlsx"]
    assert manifest["counted"] == {".jpg": 1}
    assert manifest["root"] == "raw"


def test_verify_passes_on_unchanged_files(raw_tree, tmp_path):
    base, root = raw_tree
    path = tmp_path / "m.json"
    write_manifest(_manifest(base, root), path)
    verify_manifest(path, base=base)


def test_verify_fails_on_changed_byte(raw_tree, tmp_path):
    base, root = raw_tree
    path = tmp_path / "m.json"
    write_manifest(_manifest(base, root), path)
    (root / "day1" / "logger.csv").write_bytes(b"a,b\n1,3\n")
    with pytest.raises(ManifestMismatchError, match="logger.csv"):
        verify_manifest(path, base=base)


def test_verify_fails_on_missing_file(raw_tree, tmp_path):
    base, root = raw_tree
    path = tmp_path / "m.json"
    write_manifest(_manifest(base, root), path)
    (root / "day1" / "survey.xlsx").unlink()
    with pytest.raises(ManifestMismatchError, match="missing file: day1/survey.xlsx"):
        verify_manifest(path, base=base)


def test_manifest_is_byte_identical_across_runs(raw_tree, tmp_path):
    base, root = raw_tree
    first, second = tmp_path / "a.json", tmp_path / "b.json"
    write_manifest(_manifest(base, root), first)
    write_manifest(_manifest(base, root), second)
    assert first.read_bytes() == second.read_bytes()


def test_manifest_hashes_collects_all_entries(raw_tree, tmp_path):
    base, root = raw_tree
    manifests = tmp_path / "manifests"
    write_manifest(_manifest(base, root), manifests / "x.json")
    assert len(manifest_hashes(manifests)) == 2


def test_missing_root_is_rejected(tmp_path):
    with pytest.raises(FileNotFoundError):
        build_manifest(tmp_path / "absent", {".csv"}, set(), base=tmp_path)


def test_empty_root_is_rejected(tmp_path):
    (tmp_path / "raw").mkdir()
    with pytest.raises(FileNotFoundError, match="no files"):
        build_manifest(tmp_path / "raw", {".csv"}, set(), base=tmp_path)
