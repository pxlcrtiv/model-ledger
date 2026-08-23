"""Unit tests for the canonical manifest hashing — no network required."""
import json
from pathlib import Path

import pytest

from model_ledger.manifest import (
    canonical_manifest,
    hash_manifest_bytes,
    manifest_from_local_dir,
    manifest_hash,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = REPO_ROOT / "examples" / "demo-model"

# Golden values locked by scripts/gen_golden.py — the Solidity test
# (test/ModelLedger.t.sol) embeds the same pair.
GOLDEN_HASH = "0xc6b50c4dcaeea06eaa85a10a7c26bb8faa0137b9f0928e13f344375f5efafca9"
GOLDEN_CANONICAL = (
    '{"files":[{"path":"README.md","sha256":"3c70040eaecfe1da5509a6b6f0c2b265254a26558f0206339a49f7c6e53e786e",'
    '"size":205},{"path":"config.json","sha256":"985e3e4faf1496d31c27823ad8a90848c6bef6b72ff363c1e66b48b1e0dd8e1b",'
    '"size":158}]}'
)


def test_golden_manifest_matches_solidity_fixture():
    canonical = canonical_manifest(manifest_from_local_dir(DEMO_DIR))
    assert canonical == GOLDEN_CANONICAL
    assert hash_manifest_bytes(canonical) == GOLDEN_HASH


def test_hash_is_order_independent():
    entries = [
        {"path": "b.bin", "sha256": "aa" * 32, "size": 2},
        {"path": "a.bin", "sha256": "bb" * 32, "size": 1},
    ]
    shuffled = [entries[1], entries[0]]
    assert canonical_manifest(entries) == canonical_manifest(shuffled)
    assert manifest_hash(entries) == manifest_hash(shuffled)


def test_sha256_normalization():
    with_0x = [{"path": "f", "sha256": "0x" + "ab" * 32, "size": 1}]
    without_0x = [{"path": "f", "sha256": "ab" * 32, "size": 1}]
    assert manifest_hash(with_0x) == manifest_hash(without_0x)
    assert "0x" not in canonical_manifest(with_0x)


def test_local_dir_manifest(tmp_path):
    (tmp_path / "config.json").write_text('{"a": 1}')
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "w.bin").write_bytes(bytes(range(256)))
    entries = manifest_from_local_dir(tmp_path)
    assert [e["path"] for e in entries] == ["config.json", "sub/w.bin"]
    assert entries[0]["size"] == 8
    # cross-check one sha256 with hashlib directly
    import hashlib

    assert entries[1]["sha256"] == hashlib.sha256(bytes(range(256))).hexdigest()
    assert canonical_manifest(entries).startswith('{"files":[')


def test_local_dir_rejects_missing_and_empty(tmp_path):
    with pytest.raises(NotADirectoryError):
        manifest_from_local_dir(tmp_path / "nope")
    with pytest.raises(ValueError):
        manifest_from_local_dir(tmp_path)


def test_hash_stability_across_versions():
    entries = [{"path": "x", "sha256": "cd" * 32, "size": 7}]
    h = manifest_hash(entries)
    assert h.startswith("0x") and len(h) == 66
    assert json.loads(canonical_manifest(entries))["files"][0]["path"] == "x"