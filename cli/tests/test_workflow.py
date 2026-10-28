"""Tests for TransactionWorkflow — the tx → wait → verify → print recipe."""
from unittest.mock import MagicMock, patch

from model_ledger.workflow import run_workflow


def _make_chain(tx_hash="0x" + "ab" * 32, block=1, verify_result=(True, {})):
    chain = MagicMock()
    chain.w3 = MagicMock()
    receipt = MagicMock()
    receipt.transactionHash.hex.return_value = tx_hash
    receipt.blockNumber = block
    chain.verify.return_value = verify_result
    return chain, receipt


def test_run_workflow_full_sequence():
    chain, receipt = _make_chain()
    printed = []

    def printer(line):
        printed.append(line)

    with patch("model_ledger.workflow.wait_for_latest") as mock_wait:
        run_workflow(
            chain,
            send_tx=lambda: receipt,
            repo="test/repo",
            digest="0xdigest",
            print_receipt=lambda r: printed.append(f"tx:{r.transactionHash.hex()}"),
            verify_label="verify",
            printer=printer,
        )
        mock_wait.assert_called_once_with(chain.w3)

    assert printed[0] == f"tx:{receipt.transactionHash.hex()}"
    assert printed[1] == "verify: VERIFIED ✓"
    chain.verify.assert_called_once_with("test/repo", "0xdigest")


def test_run_workflow_prints_failure_when_verify_fails():
    chain, receipt = _make_chain(verify_result=(False, {}))
    printed = []

    def printer(line):
        printed.append(line)

    with patch("model_ledger.workflow.wait_for_latest"):
        run_workflow(
            chain,
            send_tx=lambda: receipt,
            repo="test/repo",
            digest="0xdigest",
            print_receipt=lambda r: None,
            verify_label="verify",
            printer=printer,
        )

    assert printed == ["verify: FAILED ✗"]


def test_run_workflow_prints_record_when_present():
    record = {
        "repoId": "test/repo",
        "owner": "0xabc",
        "manifestHash": "0xdef",
        "metadataUri": "",
        "registeredAt": 0,
        "updatedAt": 0,
        "manifestVersion": 1,
    }
    chain, receipt = _make_chain(verify_result=(True, record))
    printed = []

    def printer(line):
        printed.append(line)

    with patch("model_ledger.workflow.wait_for_latest"):
        run_workflow(
            chain,
            send_tx=lambda: receipt,
            repo="test/repo",
            digest="0xdigest",
            print_receipt=lambda r: None,
            verify_label="verify",
            printer=printer,
        )

    # printer called twice: verify line + fmt_record(record) as one string
    assert len(printed) == 2
    assert printed[0] == "verify: VERIFIED ✓"
    assert "repoId" in printed[1]
    assert "manifestVersion  1" in printed[1]


def test_run_workflow_custom_verify_label():
    chain, receipt = _make_chain()
    printed = []

    def printer(line):
        printed.append(line)

    with patch("model_ledger.workflow.wait_for_latest"):
        run_workflow(
            chain,
            send_tx=lambda: receipt,
            repo="r",
            digest="0xd",
            print_receipt=lambda r: None,
            verify_label="on-chain verify after register",
            printer=printer,
        )

    assert printed[0] == "on-chain verify after register: VERIFIED ✓"


def test_run_workflow_default_printer_is_print(capsys):
    chain, receipt = _make_chain()

    with patch("model_ledger.workflow.wait_for_latest"):
        # Omit printer to use the default (print)
        run_workflow(
            chain,
            send_tx=lambda: receipt,
            repo="r",
            digest="0xd",
            print_receipt=lambda r: None,
        )

    captured = capsys.readouterr()
    assert "VERIFIED" in captured.out
