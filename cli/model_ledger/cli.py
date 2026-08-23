"""Click-based command-line interface for ModelLedger."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click

from . import __version__
from .chain import Chain, fmt_record, network_tag, wait_for_latest
from .manifest import (
    canonical_manifest,
    hash_manifest_bytes,
    manifest_from_hf,
    manifest_from_local_dir,
    manifest_hash,
)

DEFAULT_RPC = "http://127.0.0.1:8545"
ANVIL_DEV_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"


def _key_option(f):
    return click.option(
        "--key", envvar="MODEL_LEDGER_PRIVATE_KEY", help="Private key (0x…). Env: MODEL_LEDGER_PRIVATE_KEY."
    )(f)


def _rpc_option(f):
    return click.option(
        "--rpc", envvar="MODEL_LEDGER_RPC_URL", default=DEFAULT_RPC, show_default=True,
        help="EVM RPC endpoint. Env: MODEL_LEDGER_RPC_URL.",
    )(f)


def _contract_option(f):
    return click.option(
        "--contract", envvar="MODEL_LEDGER_CONTRACT", default=None,
        help="Deployed contract address (overrides deployments/<network>.json).",
    )(f)


@click.group()
@click.version_option(__version__)
def cli():
    """ModelLedger — register and verify ML model artifact manifests on-chain."""


# --------------------------------------------------------------------- manifest


@cli.command("manifest")
@click.option("--repo", default=None, help="Hugging Face repo id, e.g. black-forest-labs/FLUX.1-dev.")
@click.option("--local-dir", default=None, type=click.Path(exists=True, file_okay=False), help="Local model directory.")
@click.option("--output", "-o", default=None, type=click.Path(), help="Write the canonical manifest JSON to this file.")
@click.option("--max-download-mb", default=50, show_default=True, help="Cap on downloaded bytes for non-LFS files.")
def manifest_cmd(repo, local_dir, output, max_download_mb):
    """Build the canonical manifest of a model and print its keccak256 hash.

    Exactly one of --repo / --local-dir is required.
    """
    if bool(repo) == bool(local_dir):
        raise click.UsageError("pass exactly one of --repo or --local-dir")
    entries = manifest_from_hf(repo, max_download_mb) if repo else manifest_from_local_dir(Path(local_dir))
    canonical = canonical_manifest(entries)
    digest = hash_manifest_bytes(canonical)
    if output:
        out = Path(output)
        out.write_text(canonical + "\n")
        click.echo(f"manifest written to {out} ({len(entries)} files)")
    else:
        click.echo(canonical)
    click.echo(f"hash: {digest}")


# -------------------------------------------------------------------- register


@cli.command("register")
@click.argument("repo")
@click.option("--hash", "hash_", default=None, help="Manifest hash (0x…) to register.")
@click.option("--manifest", "manifest_file", default=None, type=click.Path(exists=True, dir_okay=False),
              help="Canonical manifest file whose hash is registered.")
@click.option("--uri", default="", help="Optional metadata URI (ipfs://, https://…).")
@_key_option
@_rpc_option
@_contract_option
def register_cmd(repo, hash_, manifest_file, uri, key, rpc, contract):
    """Register a model's manifest hash on-chain."""
    if bool(hash_) == bool(manifest_file):
        raise click.UsageError("pass exactly one of --hash or --manifest")
    digest = hash_ if hash_ else hash_manifest_bytes(Path(manifest_file).read_text().strip())
    if not key:
        raise click.UsageError("--key required (or set MODEL_LEDGER_PRIVATE_KEY)")
    chain = Chain.connect(rpc, contract)
    if chain.is_registered(repo):
        click.echo(f"already registered: {repo}")
        sys.exit(1)
    receipt = chain.register(key, repo, digest, uri)
    click.echo(f"tx:      {receipt.transactionHash.hex()}")
    click.echo(f"block:   {receipt.blockNumber}")
    click.echo(f"from:    {receipt['from']}")
    click.echo(f"contract:{chain.address}")
    wait_for_latest(chain.w3)
    ok, record = chain.verify(repo, digest)
    click.echo("on-chain verify after register: " + ("VERIFIED ✓" if ok else "FAILED ✗"))
    if record:
        click.echo(fmt_record(record))


# ---------------------------------------------------------------------- verify


@cli.command("verify")
@click.argument("repo")
@click.option("--hash", "hash_", default=None, help="Manifest hash (0x…) to check.")
@click.option("--manifest", "manifest_file", default=None, type=click.Path(exists=True, dir_okay=False),
              help="Canonical manifest file to check (re-hashed locally).")
@_rpc_option
@_contract_option
def verify_cmd(repo, hash_, manifest_file, rpc, contract):
    """Check whether a manifest hash is registered on-chain."""
    if bool(hash_) == bool(manifest_file):
        raise click.UsageError("pass exactly one of --hash or --manifest")
    digest = hash_ if hash_ else hash_manifest_bytes(Path(manifest_file).read_text().strip())
    chain = Chain.connect(rpc, contract)
    ok, record = chain.verify(repo, digest)
    if ok:
        click.echo(f"{repo} VERIFIED ✓ — manifest hash is registered")
    else:
        click.echo(f"{repo} NOT VERIFIED ✗ — hash mismatch or not registered")
    if record and record["repoId"]:
        click.echo(fmt_record(record))


# ------------------------------------------------------------------------- get


@cli.command("get")
@click.argument("repo")
@_rpc_option
@_contract_option
def get_cmd(repo, rpc, contract):
    """Print the on-chain record for a repo id."""
    chain = Chain.connect(rpc, contract)
    click.echo(fmt_record(chain.get(repo)))


@cli.command("list")
@_rpc_option
@_contract_option
def list_cmd(rpc, contract):
    """List every registered repo id."""
    chain = Chain.connect(rpc, contract)
    ids = chain.all_repo_ids()
    click.echo(f"{len(ids)} registered model(s)")
    for i in ids:
        click.echo(f"  {i}")


# ----------------------------------------------------------------------- update


@cli.command("update")
@click.argument("repo")
@click.option("--hash", "hash_", required=True, help="New manifest hash (0x…).")
@click.option("--uri", default="", help="New metadata URI.")
@_key_option
@_rpc_option
@_contract_option
def update_cmd(repo, hash_, uri, key, rpc, contract):
    """Update a manifest hash you own."""
    if not key:
        raise click.UsageError("--key required (or set MODEL_LEDGER_PRIVATE_KEY)")
    chain = Chain.connect(rpc, contract)
    receipt = chain.update_manifest(key, repo, hash_, uri)
    click.echo(f"tx:    {receipt.transactionHash.hex()}")
    click.echo(f"block: {receipt.blockNumber}")
    wait_for_latest(chain.w3)
    ok, record = chain.verify(repo, hash_)
    click.echo("on-chain verify after update: " + ("VERIFIED ✓" if ok else "FAILED ✗"))


# --------------------------------------------------------------------- deploy


@cli.command("deploy")
@_key_option
@_rpc_option
def deploy_cmd(key, rpc):
    """Deploy a fresh ModelLedger and save deployments/<network>.json."""
    if not key:
        raise click.UsageError("--key required (or set MODEL_LEDGER_PRIVATE_KEY)")
    address, path = Chain.deploy(rpc, key)
    click.echo(f"ModelLedger deployed at {address}")
    click.echo(f"saved deployment info: {path}")


# ------------------------------------------------------------------------ demo


@cli.command("demo")
@click.option("--repo", default="pxlcrtiv/demo-model", show_default=True, help="Repo id to register in the demo.")
@_rpc_option
def demo_cmd(repo, rpc):
    """End-to-end local demo: deploy to anvil, register examples/demo-model, verify.

    Requires a running anvil (forge install ships one):  anvil --port 8545
    """
    tag = network_tag(rpc)
    if tag != "anvil":
        click.echo(f"demo targets a local anvil chain, got '{rpc}' — start one: `anvil`", err=True)
        sys.exit(1)
    from .chain import deployed_address

    key = ANVIL_DEV_KEY  # anvil's pre-funded dev account 0
    click.echo("── model-ledger demo ──────────────────────────────────────")
    deploy_path = ""
    if deployed_address(tag):
        click.echo(f"reusing deployment {deployed_address(tag)} (delete deployments/anvil.json to redeploy)")
    else:
        address, deploy_path = Chain.deploy(rpc, key)
        click.echo(f"deployed: {address}")
    chain = Chain.connect(rpc)

    demo_dir = Path(__file__).resolve().parents[2] / "examples" / "demo-model"
    entries = manifest_from_local_dir(demo_dir)
    canonical = canonical_manifest(entries)
    digest = hash_manifest_bytes(canonical)
    click.echo(f"manifest ({len(entries)} files, {demo_dir}):")
    click.echo(f"  hash: {digest}")

    if chain.is_registered(repo):
        click.echo(f"'{repo}' exists — updating instead")
        receipt = chain.update_manifest(key, repo, digest, "")
        action = "updated"
    else:
        receipt = chain.register(key, repo, digest, "")
        action = "registered"
    click.echo(f"{action}: tx {receipt.transactionHash.hex()} (block {receipt.blockNumber})")
    wait_for_latest(chain.w3)

    ok, record = chain.verify(repo, digest)
    click.echo("verify:  " + ("VERIFIED ✓" if ok else "NOT VERIFIED ✗"))
    click.echo(fmt_record(record))
    click.echo(f"total:   {chain.total_models()} model(s) registered")
    click.echo("── demo complete ──────────────────────────────────────────")
    click.echo(f"contract address: {chain.address}  (saved in {deploy_path or 'deployments/anvil.json'})")


def main():
    cli()


if __name__ == "__main__":
    main()