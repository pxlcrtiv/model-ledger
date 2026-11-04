"""Unit tests for Chain — deep EVM adapter returning ModelRecord objects."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys_path = str(REPO_ROOT / "cli")
import sys

sys.path.insert(0, sys_path)

from model_ledger.chain import (
    Chain,
    ModelRecord,
    deployed_address,
    load_artifact,
    network_tag,
    save_deployed,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_contract_mock(verify_record_tuple=None):
    """Return a mock contract.

    verify_record_tuple: the raw tuple returned inside the verifyModel /
    verifyManifest response (i.e., the second element of the (bool, tuple) pair).
    """
    contract = MagicMock()

    # verifyModel / verifyManifest -> (bool, record_tuple)
    verify_fn = MagicMock()
    if verify_record_tuple is not None:
        verify_fn.call.return_value = (True, verify_record_tuple)
    else:
        verify_fn.call.return_value = (True, ("0x0", bytes(32), "", "", 0, 0, 0))
    contract.functions.verifyModel.return_value = verify_fn
    contract.functions.verifyManifest.return_value = verify_fn

    # getModel -> record_tuple directly
    get_fn = MagicMock()
    get_fn.call.return_value = verify_record_tuple or ("0x0", bytes(32), "", "", 0, 0, 0)
    contract.functions.getModel.return_value = get_fn

    # isRegistered -> bool
    reg_fn = MagicMock()
    reg_fn.call.return_value = True
    contract.functions.isRegistered.return_value = reg_fn

    # allRepoIds -> list[str]
    ar_fn = MagicMock()
    ar_fn.call.return_value = []
    contract.functions.allRepoIds.return_value = ar_fn

    # totalModels -> int
    tm_fn = MagicMock()
    tm_fn.call.return_value = 0
    contract.functions.totalModels.return_value = tm_fn

    return contract


def _make_w3_mock():
    """Plain MagicMock with the eth namespace set up."""
    w3 = MagicMock()
    w3.is_connected.return_value = True
    w3.eth.chain_id = 31337
    w3.eth.max_priority_fee = w3.to_wei.return_value = 1000000000
    w3.eth.get_block.return_value = {"baseFeePerGas": 2000000000}
    w3.eth.get_transaction_count.return_value = 0
    w3.eth.wait_for_transaction_receipt.return_value = MagicMock(status=1)
    account_mock = MagicMock()
    account_mock.address = "0xfrom"
    account_mock.sign_transaction.return_value = MagicMock(raw_transaction=b"raw")
    w3.eth.account.from_key.return_value = account_mock
    w3.eth.account.create.return_value = MagicMock(address="0xother")
    return w3


def _sample_record_tuple():
    return (
        "0xabcdef1234567890",
        bytes.fromhex("ab" * 32),
        "test/repo",
        "ipfs://QmTest",
        1700000000,
        1700000001,
        1,
    )


# ---------------------------------------------------------------------------
# ModelRecord
# ---------------------------------------------------------------------------

class TestModelRecord:
    def test_from_tuple_populates_fields(self):
        rec_tuple = _sample_record_tuple()
        rec = ModelRecord.from_tuple(rec_tuple)
        assert rec.owner == "0xabcdef1234567890"
        assert rec.manifest_hash == "0x" + "ab" * 32
        assert rec.repo_id == "test/repo"
        assert rec.metadata_uri == "ipfs://QmTest"
        assert rec.registered_at == 1700000000
        assert rec.updated_at == 1700000001
        assert rec.manifest_version == 1

    def test_to_dict_returns_all_fields(self):
        rec = ModelRecord(
            owner="0xowner",
            manifest_hash="0xhash",
            repo_id="r",
            metadata_uri="",
            registered_at=1,
            updated_at=2,
            manifest_version=3,
        )
        d = rec.to_dict()
        assert d["owner"] == "0xowner"
        assert d["manifestHash"] == "0xhash"
        assert d["repoId"] == "r"
        assert d["metadataUri"] == ""
        assert d["registeredAt"] == 1
        assert d["updatedAt"] == 2
        assert d["manifestVersion"] == 3

    def test_dict_like_get_and_getitem(self):
        rec = ModelRecord(
            owner="0xowner",
            manifest_hash="0xh",
            repo_id="r",
            metadata_uri="",
            registered_at=0,
            updated_at=0,
            manifest_version=1,
        )
        assert rec.get("repoId") == "r"
        assert rec.get("missing", "default") == "default"
        assert rec["repoId"] == "r"
        assert rec["manifestVersion"] == 1


# ---------------------------------------------------------------------------
# network_tag / deployed_address / save_deployed / load_artifact
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_network_tag_localhost(self):
        assert network_tag("http://127.0.0.1:8545") == "anvil"
        assert network_tag("http://localhost:8545") == "anvil"

    def test_network_tag_remote(self):
        assert network_tag("https://sepolia.infura.io/v3/abc") == "sepolia"

    def test_deployed_address_missing(self):
        assert deployed_address("nonexistent") is None

    def test_save_and_load_deployed(self, tmp_path):
        tag = "anvil"
        path = save_deployed(tag, "0xabc", 31337, "0xtx", deployments_dir=tmp_path)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["address"] == "0xabc"
        assert data["chainId"] == 31337
        assert data["deployTx"] == "0xtx"
        assert deployed_address(tag, deployments_dir=tmp_path) == "0xabc"

    def test_load_artifact(self):
        artifact = load_artifact()
        assert "abi" in artifact
        assert "bytecode" in artifact


# ---------------------------------------------------------------------------
# Chain.connect
# ---------------------------------------------------------------------------

class TestChainConnect:
    def test_connect_returns_chain(self):
        mock_w3 = MagicMock()
        mock_w3.is_connected.return_value = True
        mock_w3.to_checksum_address.side_effect = lambda x: x

        with patch("model_ledger.chain.load_artifact", return_value={"abi": [], "bytecode": "0x"}), \
             patch("model_ledger.chain.Web3", return_value=mock_w3), \
             patch("model_ledger.chain.deployed_address", return_value="0xcontract"), \
             patch("model_ledger.chain.Web3.to_checksum_address", side_effect=lambda x: x):
            chain = Chain.connect("http://127.0.0.1:8545")

        assert isinstance(chain, Chain)
        assert chain.address == "0xcontract"

    def test_connect_raises_when_no_contract(self):
        mock_w3 = MagicMock()
        mock_w3.is_connected.return_value = True

        with patch("model_ledger.chain.Web3", return_value=mock_w3), \
             patch("model_ledger.chain.deployed_address", return_value=None), \
             pytest.raises(SystemExit):
            Chain.connect("http://127.0.0.1:8545")

    def test_connect_raises_when_rpc_down(self):
        mock_w3 = MagicMock()
        mock_w3.is_connected.return_value = False

        with patch("model_ledger.chain.Web3", return_value=mock_w3), \
             pytest.raises(ConnectionError):
            Chain.connect("http://127.0.0.1:8545")


# ---------------------------------------------------------------------------
# Chain reads
# ---------------------------------------------------------------------------

class TestChainReads:
    def test_verify_returns_model_record(self):
        verify_record_tuple = _sample_record_tuple()
        contract = _make_contract_mock(verify_record_tuple)
        w3 = _make_w3_mock()
        chain = Chain.__new__(Chain)
        chain._w3 = w3
        chain._address = "0xcontract"
        chain._contract = contract

        ok, record = chain.verify("test/repo", "0xdigest")

        assert ok is True
        assert isinstance(record, ModelRecord)
        assert record.repo_id == "test/repo"
        contract.functions.verifyModel.assert_called_once_with("test/repo", "0xdigest")

    def test_verify_returns_false_with_empty_record_when_not_found(self):
        empty_tuple = ("0x0", bytes(32), "", "", 0, 0, 0)
        contract = MagicMock()
        verify_fn = MagicMock()
        verify_fn.call.return_value = (False, empty_tuple)
        contract.functions.verifyModel.return_value = verify_fn
        contract.functions.verifyManifest.return_value = verify_fn
        w3 = _make_w3_mock()
        chain = Chain.__new__(Chain)
        chain._w3 = w3
        chain._address = "0xcontract"
        chain._contract = contract

        ok, record = chain.verify("missing/repo", "0xdigest")

        assert ok is False
        assert isinstance(record, ModelRecord)
        assert record.repo_id == ""

    def test_get_returns_model_record(self):
        rec_tuple = _sample_record_tuple()
        contract = _make_contract_mock(rec_tuple)
        w3 = _make_w3_mock()
        chain = Chain.__new__(Chain)
        chain._w3 = w3
        chain._address = "0xcontract"
        chain._contract = contract

        record = chain.get("test/repo")

        assert isinstance(record, ModelRecord)
        assert record.repo_id == "test/repo"

    def test_is_registered(self):
        contract = _make_contract_mock(None)
        w3 = _make_w3_mock()
        chain = Chain.__new__(Chain)
        chain._w3 = w3
        chain._address = "0xcontract"
        chain._contract = contract

        assert chain.is_registered("test/repo") is True
        contract.functions.isRegistered.assert_called_once_with("test/repo")

    def test_all_repo_ids(self):
        contract = _make_contract_mock(None)
        contract.functions.allRepoIds.return_value.call.return_value = ["a", "b"]
        w3 = _make_w3_mock()
        chain = Chain.__new__(Chain)
        chain._w3 = w3
        chain._address = "0xcontract"
        chain._contract = contract

        assert chain.all_repo_ids() == ["a", "b"]

    def test_total_models(self):
        contract = _make_contract_mock(None)
        contract.functions.totalModels.return_value.call.return_value = 42
        w3 = _make_w3_mock()
        chain = Chain.__new__(Chain)
        chain._w3 = w3
        chain._address = "0xcontract"
        chain._contract = contract

        assert chain.total_models() == 42


# ---------------------------------------------------------------------------
# Chain writes (tx lifecycle encapsulated)
# ---------------------------------------------------------------------------

class TestChainWrites:
    def test_register_executes_full_tx_lifecycle(self):
        w3 = _make_w3_mock()
        contract = _make_contract_mock(None)

        chain = Chain.__new__(Chain)
        chain._w3 = w3
        chain._address = "0xcontract"
        chain._contract = contract

        receipt = chain.register("0xkey", "test/repo", "0xdigest", "")

        assert receipt.status == 1
        contract.functions.registerModel.assert_called_once_with("test/repo", "0xdigest", "")

    def test_update_manifest_executes_full_tx_lifecycle(self):
        w3 = _make_w3_mock()
        contract = _make_contract_mock(None)

        chain = Chain.__new__(Chain)
        chain._w3 = w3
        chain._address = "0xcontract"
        chain._contract = contract

        receipt = chain.update_manifest("0xkey", "test/repo", "0xnewdigest", "")

        assert receipt.status == 1
        contract.functions.updateManifest.assert_called_once_with("test/repo", "0xnewdigest", "")

    def test_transfer_ownership_executes_full_tx_lifecycle(self):
        w3 = _make_w3_mock()
        contract = _make_contract_mock(None)

        chain = Chain.__new__(Chain)
        chain._w3 = w3
        chain._address = "0xcontract"
        chain._contract = contract

        receipt = chain.transfer_ownership("0xkey", "test/repo", "0xnewowner")

        assert receipt.status == 1
        contract.functions.transferOwnership.assert_called_once_with("test/repo", "0xnewowner")


# ---------------------------------------------------------------------------
# Chain.deploy
# ---------------------------------------------------------------------------

class TestChainDeploy:
    def test_deploy_saves_and_returns_address(self, tmp_path):
        artifact = {"abi": [], "bytecode": {"object": "0xdeadbeef"}}
        mock_w3 = MagicMock()
        mock_w3.is_connected.return_value = True
        mock_w3.eth.chain_id = 31337
        receipt = MagicMock()
        receipt.contractAddress = "0xdeployed"
        receipt.status = 1
        mock_w3.eth.wait_for_transaction_receipt.return_value = receipt
        mock_w3.eth.get_transaction_count.return_value = 0
        mock_w3.to_wei.return_value = 1000000000
        account_mock = MagicMock()
        account_mock.address = "0xfrom"
        account_mock.sign_transaction.return_value = MagicMock(raw_transaction=b"raw")
        mock_w3.eth.account.from_key.return_value = account_mock

        with patch("model_ledger.chain.load_artifact", return_value=artifact), \
             patch("model_ledger.chain.Web3", return_value=mock_w3), \
             patch("model_ledger.chain.save_deployed") as mock_save, \
             patch("model_ledger.chain.network_tag", return_value="anvil"):
            mock_save.return_value = tmp_path / "anvil.json"
            address, path = Chain.deploy("http://127.0.0.1:8545", "0xkey")

        assert address == "0xdeployed"
        assert path == tmp_path / "anvil.json"
        mock_save.assert_called_once()


# ---------------------------------------------------------------------------
# Fee params
# ---------------------------------------------------------------------------

class TestFeeParams:
    def test_fee_params_returns_dict_with_required_keys(self):
        w3 = _make_w3_mock()
        params = Chain._fee_params(w3)
        assert "maxPriorityFeePerGas" in params
        assert "maxFeePerGas" in params
        assert params["maxFeePerGas"] >= params["maxPriorityFeePerGas"]
