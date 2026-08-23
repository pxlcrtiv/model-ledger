#!/usr/bin/env python3
"""Cross-check keccak256 implementations (pycryptodome vs web3)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cli"))
from model_ledger.manifest import hash_manifest_bytes

CANONICAL = '{"files":[{"path":"README.md","sha256":"3c70040eaecfe1da5509a6b6f0c2b265254a26558f0206339a49f7c6e53e786e","size":205},{"path":"config.json","sha256":"985e3e4faf1496d31c27823ad8a90848c6bef6b72ff363c1e66b48b1e0dd8e1b","size":158}]}'

from web3 import Web3
w3hash = Web3.keccak(text=CANONICAL).hex()
pyhash = hash_manifest_bytes(CANONICAL)
print("web3 :", w3hash)
print("pydom:", pyhash)
assert w3hash == pyhash.removeprefix("0x"), "MISMATCH!"
print("keccak implementations agree")