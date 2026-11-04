"""Ethereum interaction layer (web3.py) for ModelLedger.

Everything talks to *any* EVM chain — local anvil for demos, Sepolia for the
real registry. The contract holds no value, so this code never moves tokens.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from web3 import Web3
from web3.types import TxReceipt

ARTIFACT = Path(__file__).parent / "abi" / "ModelLedger.json"
DEFAULT_RPC = "http://127.0.0.1:8545"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEPLOYMENTS_DIR = REPO_ROOT / "deployments"


def load_artifact() -> dict:
    with open(ARTIFACT) as f:
        return json.load(f)


def network_tag(rpc: str) -> str:
    """'anvil' for localhost RPCs, otherwise the host-derived tag."""
    if "127.0.0.1" in rpc or "localhost" in rpc:
        return "anvil"
    return "sepolia"


def deployed_address(tag: str, *, deployments_dir: Path = DEPLOYMENTS_DIR) -> str | None:
    path = deployments_dir / f"{tag}.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f).get("address")


def save_deployed(
    tag: str,
    address: str,
    chain_id: int,
    tx_hash: str,
    *,
    deployments_dir: Path = DEPLOYMENTS_DIR,
) -> Path:
    path = deployments_dir / f"{tag}.json"
    data = {"network": tag, "chainId": chain_id, "address": address, "deployTx": tx_hash}
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    return path


@dataclass
class ModelRecord:
    """Rich representation of a ModelLedger on-chain record."""

    owner: str
    manifest_hash: str
    repo_id: str
    metadata_uri: str
    registered_at: int
    updated_at: int
    manifest_version: int

    @classmethod
    def from_tuple(cls, rec: tuple) -> ModelRecord:
        """Build a ModelRecord from the Solidity tuple returned by contract calls."""
        return cls(
            owner=rec[0],
            manifest_hash="0x" + rec[1].hex(),
            repo_id=rec[2],
            metadata_uri=rec[3],
            registered_at=int(rec[4]),
            updated_at=int(rec[5]),
            manifest_version=int(rec[6]),
        )

    def to_dict(self) -> dict:
        return {
            "owner": self.owner,
            "manifestHash": self.manifest_hash,
            "repoId": self.repo_id,
            "metadataUri": self.metadata_uri,
            "registeredAt": self.registered_at,
            "updatedAt": self.updated_at,
            "manifestVersion": self.manifest_version,
        }

    def get(self, key: str, default=None):
        """Dict-like access so fmt_record and legacy callers keep working."""
        attr = _FIELD_ALIASES.get(key, key)
        return getattr(self, attr, default)

    def __getitem__(self, key: str):
        attr = _FIELD_ALIASES.get(key, key)
        return getattr(self, attr)


_FIELD_ALIASES: Final[dict[str, str]] = {
    "repoId": "repo_id",
    "manifestHash": "manifest_hash",
    "metadataUri": "metadata_uri",
    "registeredAt": "registered_at",
    "updatedAt": "updated_at",
    "manifestVersion": "manifest_version",
}


class Chain:
    """Deep typed adapter over a ModelLedger contract instance.

    All EVM internals (web3 instance, contract object, tuple indices) are
    encapsulated.  Callers receive rich ModelRecord objects for reads and
    TxReceipt instances for writes.
    """

    def __init__(self, w3: Web3, address: str, contract: object):
        self._w3 = w3
        self._address = address
        self._contract = contract

    @property
    def address(self) -> str:
        """The checksummed ModelLedger contract address."""
        return self._address

    @classmethod
    def connect(cls, rpc: str, contract_address: str | None = None) -> Chain:
        w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 30}))
        if not w3.is_connected():
            raise ConnectionError(f"cannot reach RPC at {rpc}")
        addr = contract_address or deployed_address(network_tag(rpc))
        if not addr:
            raise SystemExit(
                f"no ModelLedger address for network '{network_tag(rpc)}'. "
                f"Deploy first (model-ledger deploy) or pass --contract."
            )
        artifact = load_artifact()
        contract = w3.eth.contract(address=Web3.to_checksum_address(addr), abi=artifact["abi"])
        return cls(w3=w3, address=Web3.to_checksum_address(addr), contract=contract)

    # ------------------------------------------------------------------ reads

    def verify(self, repo_id: str, candidate_hash: str) -> tuple[bool, ModelRecord]:
        verified, record = self._contract.functions.verifyModel(repo_id, candidate_hash).call()
        return bool(verified), ModelRecord.from_tuple(record)

    def verify_manifest(self, repo_id: str, canonical: str) -> tuple[bool, ModelRecord]:
        verified, record = self._contract.functions.verifyManifest(repo_id, canonical).call()
        return bool(verified), ModelRecord.from_tuple(record)

    def get(self, repo_id: str) -> ModelRecord:
        return ModelRecord.from_tuple(self._contract.functions.getModel(repo_id).call())

    def is_registered(self, repo_id: str) -> bool:
        return bool(self._contract.functions.isRegistered(repo_id).call())

    def all_repo_ids(self) -> list[str]:
        return list(self._contract.functions.allRepoIds().call())

    def total_models(self) -> int:
        return int(self._contract.functions.totalModels().call())

    # ------------------------------------------------------------------ tx lifecycle (encapsulated)

    @staticmethod
    def _fee_params(w3: Web3) -> dict:
        """EIP-1559 fee params that hold on anvil and public testnets."""
        try:
            tip = w3.eth.max_priority_fee
        except (AttributeError, ValueError):
            tip = w3.to_wei(1, "gwei")
        try:
            base = w3.eth.get_block("latest")["baseFeePerGas"] or 0
        except (KeyError, TypeError, ValueError):
            base = 0
        return {"maxPriorityFeePerGas": tip, "maxFeePerGas": base * 2 + tip}

    def _execute(self, fn, key: str) -> TxReceipt:
        """Build, sign, send, and wait for a transaction.

        The full tx lifecycle is encapsulated here so callers never see
        nonce, gas params, or raw signing steps.
        """
        account = self._w3.eth.account.from_key(key)
        tx = fn.build_transaction(
            {
                "from": account.address,
                "nonce": self._w3.eth.get_transaction_count(account.address),
                **self._fee_params(self._w3),
            }
        )
        signed = account.sign_transaction(tx)
        tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
        return self._w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

    def register(self, key: str, repo_id: str, manifest_hash: str, metadata_uri: str = "") -> TxReceipt:
        fn = self._contract.functions.registerModel(repo_id, manifest_hash, metadata_uri or "")
        return self._execute(fn, key)

    def update_manifest(self, key: str, repo_id: str, manifest_hash: str, metadata_uri: str = "") -> TxReceipt:
        fn = self._contract.functions.updateManifest(repo_id, manifest_hash, metadata_uri or "")
        return self._execute(fn, key)

    def transfer_ownership(self, key: str, repo_id: str, new_owner: str) -> TxReceipt:
        fn = self._contract.functions.transferOwnership(repo_id, new_owner)
        return self._execute(fn, key)

    # --------------------------------------------------------------- deployment

    @classmethod
    def deploy(cls, rpc: str, key: str) -> tuple[str, Path]:
        w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 30}))
        if not w3.is_connected():
            raise ConnectionError(f"cannot reach RPC at {rpc}")
        account = w3.eth.account.from_key(key)
        artifact = load_artifact()
        bytecode = artifact["bytecode"]
        if isinstance(bytecode, dict):
            bytecode = bytecode["object"]
        contract = w3.eth.contract(abi=artifact["abi"], bytecode=bytecode)
        tx = contract.constructor().build_transaction(
            {
                "from": account.address,
                "nonce": w3.eth.get_transaction_count(account.address),
                **cls._fee_params(w3),
            }
        )
        signed = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        address = receipt.contractAddress
        tag = network_tag(rpc)
        path = save_deployed(tag, address, int(w3.eth.chain_id), tx_hash.hex())
        return address, path


def wait_for_latest(seconds: float = 0.6) -> None:
    """Give the chain a beat so subsequent reads see the new block."""
    time.sleep(seconds)
