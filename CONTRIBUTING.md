# Contributing to model-ledger

First off: **thank you** — provenance for ML models only gets stronger with more
corpus, more chains, and more eyes on the hashing rules.

## Ground rules

- **Never break the golden hash.** The canonical manifest format is locked by
  identical fixture hashes in `test/ModelLedger.t.sol` and
  `cli/tests/test_manifest.py`. If you touch sorting, hashing, or field
  serialization, update **both** golden fixtures **in the same commit** or CI
  will (rightly) fail.
- **The contract holds nothing.** No value-transfer paths, no `payable` sugar.
  Keep it that way — this is a registry, not a vault.
- **Testnet-first.** Demo on anvil, reference deployment on Sepolia. Never
  point the deploy scripts at mainnet.
- **Keep it zero-dependency.** The contract has no OpenZeppelin imports; the
  CLI leans on web3.py + huggingface_hub + click and nothing else. New deps
  need a justification in the PR.

## Getting started

```bash
git clone --recurse-submodules https://github.com/pxlcrtiv/model-ledger
cd model-ledger
forge install                      # if submodules weren't cloned above
python -m venv .venv && source .venv/bin/activate
pip install -r cli/requirements.txt pytest
```

## Tests

```bash
forge fmt && forge test            # 18 tests: behaviors, events, fuzz, golden hash
pytest cli/tests/                  # unit tests + live anvil lifecycle (needs `anvil` on PATH)
```

CI runs all three jobs on every push/PR: **forge build + test (with `--sizes`)**,
**CLI unit tests**, and a **full lifecycle e2e on a fresh anvil**.

## How to add a feature

1. Branch off `main`: `git checkout -b feat/my-thing`
2. Small commits with honest messages (`feat:`, `fix:`, `docs:`, `test:`)
3. If it touches the manifest format: update **both** golden fixtures and add
   a cross-language test asserting the same hash in Solidity and Python.
4. If it adds a contract function: cover it with a Foundry test (behavior +
   events) — revert paths included.
5. Open the PR. Reference the issue/idea it closes.

## Daily-commit workflow (how this repo stays green)

The repo is designed for small, shippable deltas so the GitHub history bar
stays green — recruiters *do* check. Pick one of:

- **Add a demo model** to `examples/demo-model/` (any real model manifest)
- **Add a chain profile** to the deploy scripts (Arbitrum Sepolia, Base
  Sepolia, …)
- **Extend the CLI**: `get --json`, `list --limit`, `export` a registry dump
- **Docs**: improve the README, add a troubleshooting note, expand the trust
  model in ROADMAP.md
- **CI**: harden the workflow, add a Python version to the matrix

Rule: **one commit per day, never an empty commit.** If a feature is half
done, commit the tested half and continue tomorrow.

## Reporting a vulnerability

Open an issue with the pattern: the contract snippet (or CLI invocation), and
why the current trust model is wrong or insufficient. If it's a bug in hashing,
include the manifest JSON — never the private key.

## Code of conduct

Be kind, be precise. Disagreements are resolved with tests, not arguments.