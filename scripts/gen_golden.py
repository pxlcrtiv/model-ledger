#!/usr/bin/env python3
"""Generate golden manifest hashes for the Solidity + pytest cross-checks."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cli"))
from model_ledger.manifest import canonical_manifest, manifest_from_local_dir, hash_manifest_bytes

demo = Path(__file__).resolve().parents[1] / "examples" / "demo-model"
entries = manifest_from_local_dir(demo)
canonical = canonical_manifest(entries)

# Hand-assembled second case (no files on disk needed, deterministic)
hand = canonical_manifest([
    {"path": "weights.bin", "sha256": "0x" + "ab" * 32, "size": 1048576},
    {"path": "config.json", "sha256": "cd" * 32, "size": 512},
])

print("== demo-model dir ==")
print(canonical)
print("hash:", hash_manifest_bytes(canonical))
print("== hand case ==")
print(hand)
print("hash:", hash_manifest_bytes(hand))