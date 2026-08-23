"""Canonical manifest building and hashing for ModelLedger.

A *canonical manifest* is the byte-exact input that both the Python CLI and the
Solidity contract (`hashManifest`) feed to keccak256. Any tool that reproduces
the manifest gets the same hash, so provenance can be verified client-side.

Canonical form (must match this file exactly):

    {"files":[{"path":"a/b.bin","sha256":"<64 lowercase hex>","size":123}, ...]}

Rules:
  * entries sorted by `path` (Python string sort == UTF-8 byte order)
  * JSON with compact separators (",", ":") and the key order path, sha256, size
  * sha256 always lowercase hex without "0x"; size always an integer
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from Crypto.Hash import keccak  # pycryptodome: KECCAK-256 == Ethereum keccak256


def keccak256(data: bytes) -> bytes:
    """Ethereum keccak256 (KECCAK-256, not NIST SHA3-256)."""
    k = keccak.new(digest_bits=256)
    k.update(data)
    return k.digest()


def hash_manifest_bytes(canonical: str) -> str:
    """keccak256 of the canonical manifest string, as 0x-prefixed hex."""
    return "0x" + keccak256(canonical.encode("utf-8")).hex()


def _norm_sha(value: str) -> str:
    return str(value).lower().removeprefix("0x")


def canonical_manifest(entries: Iterable[dict]) -> str:
    """Normalize entries and render the canonical JSON string."""
    files = []
    for e in entries:
        files.append(
            {
                "path": str(e["path"]),
                "sha256": _norm_sha(e["sha256"]),
                "size": int(e["size"]),
            }
        )
    files.sort(key=lambda f: f["path"])
    return json.dumps({"files": files}, separators=(",", ":"), sort_keys=False)


def manifest_hash(entries: Iterable[dict]) -> str:
    """Canonical manifest hash (0x hex) for a list of file entries."""
    return hash_manifest_bytes(canonical_manifest(entries))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_from_local_dir(directory: Path) -> list[dict]:
    """Entry list from a local directory: sorted files, sha256 + size each."""
    if not directory.is_dir():
        raise NotADirectoryError(str(directory))
    entries = []
    for p in sorted(directory.rglob("*")):
        if p.is_file() and not p.is_symlink():
            entries.append({"path": str(p.relative_to(directory)), "sha256": sha256_file(p), "size": p.stat().st_size})
    if not entries:
        raise ValueError(f"no files found under {directory}")
    return entries


def manifest_from_hf(repo_id: str, max_download_mb: int = 50) -> list[dict]:
    """Entry list from a Hugging Face repo.

    Uses the Hub's file metadata: LFS files already carry an authoritative
    sha256, so nothing is downloaded for them. Small non-LFS files are
    downloaded to a temp dir and hashed locally (bounded by max_download_mb).
    """
    from huggingface_hub import HfApi

    api = HfApi()
    info = api.model_info(repo_id, files_metadata=True)

    entries: list[dict] = []
    budget = max_download_mb * 1024 * 1024
    for s in sorted(info.siblings or [], key=lambda s: s.rfilename):
        path = s.rfilename
        size = s.size or 0
        # LFS files expose their real sha256 in metadata — trust it, no download.
        if getattr(s, "lfs", None) is not None and s.lfs.sha256:
            entries.append({"path": path, "sha256": s.lfs.sha256, "size": size})
            continue
        if size > budget:
            raise RuntimeError(
                f"{path} is {size} bytes and not LFS-hashed; re-run with a higher "
                f"--max-download-mb or use --local-dir with a local copy"
            )
        budget -= size
        from huggingface_hub import hf_hub_download
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            local = hf_hub_download(repo_id, path, cache_dir=tmp)
            entries.append({"path": path, "sha256": sha256_file(Path(local)), "size": size})
    return entries