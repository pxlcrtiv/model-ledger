"""Live integration tests — run against a local anvil chain.

Skipped automatically when no anvil is listening on 127.0.0.1:8545.
Start one with:  anvil
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from web3 import Web3

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "cli"))

from model_ledger.chain import Chain, deployed_address, network_tag  # noqa: E402
from model_ledger.cli import ANVIL_DEV_KEY  # noqa: E402
from model_ledger.manifest import canonical_manifest, hash_manifest_bytes, manifest_from_local_dir  # noqa: E402

RPC = os.environ.get("MODEL_LEDGER_RPC_URL", "http://127.0.0.1:8545")


def _anvil_alive() -> bool:
    try:
        w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs={"timeout": 2}))
        return w3.is_connected()
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _anvil_alive(), reason="anvil not listening on localhost:8545")


def _demo_manifest_hash() -> str:
    demo = REPO_ROOT / "examples" / "demo-model"
    return hash_manifest_bytes(canonical_manifest(manifest_from_local_dir(demo)))


def test_full_lifecycle_on_anvil():
    assert network_tag(RPC) == "anvil"
    # fresh deployment for a deterministic test
    deploy_path = REPO_ROOT / "deployments" / "anvil.json"
    if deploy_path.exists():
        deploy_path.unlink()
    address, path = Chain.deploy(RPC, ANVIL_DEV_KEY)
    assert path == deploy_path
    assert Web3.is_checksum_address(address)
    assert deployed_address("anvil") == address

    chain = Chain.connect(RPC)
    digest = _demo_manifest_hash()
    account = chain.w3.eth.account.from_key(ANVIL_DEV_KEY)

    # register
    receipt = chain.register(ANVIL_DEV_KEY, "test/flow-model", digest, "ipfs://QmTest")
    assert receipt.status == 1
    ok, record = chain.verify("test/flow-model", digest)
    assert ok
    assert record["owner"] == account.address
    assert record["manifestVersion"] == 1
    assert chain.is_registered("test/flow-model")
    assert chain.total_models() == 1

    # tampered hash must fail
    ok, _ = chain.verify("test/flow-model", "0x" + "11" * 32)
    assert not ok

    # update by owner
    v2 = "0x" + "22" * 32
    receipt = chain.update_manifest(ANVIL_DEV_KEY, "test/flow-model", v2)
    assert receipt.status == 1
    ok, record = chain.verify("test/flow-model", v2)
    assert ok
    assert record["manifestVersion"] == 2

    # transfer + non-owner cannot update
    other = chain.w3.eth.account.create()
    receipt = chain.transfer_ownership(ANVIL_DEV_KEY, "test/flow-model", other.address)
    assert receipt.status == 1
    assert chain.get("test/flow-model")["owner"] == other.address
    with pytest.raises(Exception):
        chain.update_manifest(ANVIL_DEV_KEY, "test/flow-model", "0x" + "33" * 32)

    # enumeration
    assert chain.all_repo_ids() == ["test/flow-model"]


def test_register_duplicate_rejected_on_anvil():
    address, _ = Chain.deploy(RPC, ANVIL_DEV_KEY)
    chain = Chain.connect(RPC, address)
    digest = _demo_manifest_hash()
    chain.register(ANVIL_DEV_KEY, "test/dup", digest, "")
    with pytest.raises(Exception):
        chain.register(ANVIL_DEV_KEY, "test/dup", digest, "")