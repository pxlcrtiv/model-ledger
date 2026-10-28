"""Transaction workflow — reusable tx → wait → verify → print recipe."""
from __future__ import annotations

from collections.abc import Callable

from .chain import Chain, wait_for_latest

Printer = Callable[[str], None]


def run_workflow(
    chain: Chain,
    *,
    send_tx,
    repo: str,
    digest: str,
    print_receipt: Callable[[object], None],
    verify_label: str = "on-chain verify",
    printer: Printer = print,
) -> None:
    """Execute the common tx → wait → verify → print recipe.

    Parameters:
        chain: Connected Chain instance.
        send_tx: Zero-arg callable that submits the transaction and returns a receipt.
        repo: Repo id to verify against.
        digest: Manifest hash to verify.
        print_receipt: Callable that prints receipt details, given the receipt.
        verify_label: Prefix for the verification status line.
        printer: Output function (default: print; use click.echo in CLI).
    """
    receipt = send_tx()
    print_receipt(receipt)
    wait_for_latest(chain.w3)
    ok, record = chain.verify(repo, digest)
    printer(f"{verify_label}: {'VERIFIED ✓' if ok else 'FAILED ✗'}")
    if record:
        from .formatter import fmt_record

        printer(fmt_record(record))
