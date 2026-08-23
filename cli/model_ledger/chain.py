"""Ethereum interaction layer (web3.py) for ModelLedger.

Everything talks to *any* EVM chain — local anvil for demos, Sepolia for the
real registry. The contract holds no value, so this code never moves tokens.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

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


def deployed_address(tag: str) -> str | None:
    path = DEPLOYMENTS_DIR / f"{tag}.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f).get("address")


def save_deployed(tag: str, address: str, chain_id: int, tx_hash: str) -> Path:
    path = DEPLOYMENTS_DIR / f"{tag}.json"
    data = {"network": tag, "chainId": chain_id, "address": address, "deployTx": tx_hash}
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    return path


@dataclass
class Chain:
    """Thin typed wrapper over a ModelLedger contract instance."""

    w3: Web3
    address: str
    contract: object

    @classmethod
    def connect(cls, rpc: str, contract_address: str | None = None) -> "Chain":
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

    def verify(self, repo_id: str, candidate_hash: str) -> tuple[bool, dict]:
        verified, record = self.contract.functions.verifyModel(repo_id, candidate_hash).call()
        return bool(verified), self._record_dict(record)

    def verify_manifest(self, repo_id: str, canonical: str) -> tuple[bool, dict]:
        verified, record = self.contract.functions.verifyManifest(repo_id, canonical).call()
        return bool(verified), self._record_dict(record)

    def get(self, repo_id: str) -> dict:
        return self._record_dict(self.contract.functions.getModel(repo_id).call())

    def is_registered(self, repo_id: str) -> bool:
        return bool(self.contract.functions.isRegistered(repo_id).call())

    def all_repo_ids(self) -> list[str]:
        return list(self.contract.functions.allRepoIds().call())

    def total_models(self) -> int:
        return int(self.contract.functions.totalModels().call())

    @staticmethod
    def _record_dict(rec: dict) -> dict:
        return {
            "owner": rec[0],
            "manifestHash": "0x" + rec[1].hex(),
            "repoId": rec[2],
            "metadataUri": rec[3],
            "registeredAt": int(rec[4]),
            "updatedAt": int(rec[5]),
            "manifestVersion": int(rec[6]),
        }

    @staticmethod
    def _fee_params(w3: Web3) -> dict:
        """EIP-1559 fee params that hold on anvil and public testnets."""
        try:
            tip = w3.eth.max_priority_fee
        except Exception:
            tip = w3.to_wei(1, "gwei")
        try:
            base = w3.eth.get_block("latest")["baseFeePerGas"] or 0
        except Exception:
            base = 0
        return {"maxPriorityFeePerGas": tip, "maxFeePerGas": base * 2 + tip}

    # ------------------------------------------------------------------ writes

    def _send(self, fn, account) -> TxReceipt:
        tx = fn.build_transaction(
            {
                "from": account.address,
                "nonce": self.w3.eth.get_transaction_count(account.address),
                **self._fee_params(self.w3),
            }
        )
        signed = account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

    def register(self, key: str, repo_id: str, manifest_hash: str, metadata_uri: str = "") -> TxReceipt:
        account = self.w3.eth.account.from_key(key)
        fn = self.contract.functions.registerModel(repo_id, manifest_hash, metadata_uri or "")
        return self._send(fn, account)

    def update_manifest(self, key: str, repo_id: str, manifest_hash: str, metadata_uri: str = "") -> TxReceipt:
        account = self.w3.eth.account.from_key(key)
        fn = self.contract.functions.updateManifest(repo_id, manifest_hash, metadata_uri or "")
        return self._send(fn, account)

    def transfer_ownership(self, key: str, repo_id: str, new_owner: str) -> TxReceipt:
        account = self.w3.eth.account.from_key(key)
        fn = self.contract.functions.transferOwnership(repo_id, new_owner)
        return self._send(fn, account)

    # --------------------------------------------------------------- deployment

    @classmethod
    def deploy(cls, rpc: str, key: str) -> tuple[str, Path]:
        w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 30}))
        if not w3.is_connected():
            raise ConnectionError(f"cannot reach RPC at {rpc}")
        account = w3.eth.account.from_key(key)
        artifact = load_artifact()
        bytecode = artifact["bytecode"]
        # foundry artifacts nest the hex under bytecode.object
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


def fmt_record(rec: dict) -> str:
    import datetime as _dt

    def ts(x: int) -> str:
        return _dt.datetime.fromtimestamp(x, tz=_dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    return (
        f"  repoId           {rec['repoId']}\n"
        f"  owner            {rec['owner']}\n"
        f"  manifestHash     {rec['manifestHash']}\n"
        f"  metadataUri      {rec['metadataUri'] or '-'}\n"
        f"  registeredAt     {ts(rec['registeredAt'])}\n"
        f"  updatedAt        {ts(rec['updatedAt'])}\n"
        f"  manifestVersion  {rec['manifestVersion']}"
    )


def wait_for_latest(w3: Web3, seconds: float = 0.6) -> None:
    """Give the chain a beat so subsequent reads see the new block."""
    time.sleep(seconds)