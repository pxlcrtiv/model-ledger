# ModelLedger

**On-chain provenance for machine-learning models: hash your model's manifest, register it on-chain, let anyone verify it. No trusted third party.**

[![CI](https://github.com/pxlcrtiv/model-ledger/actions/workflows/ci.yml/badge.svg)](https://github.com/pxlcrtiv/model-ledger/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/github/license/pxlcrtiv/model-ledger)](LICENSE)
[![Stars](https://img.shields.io/github/stars/pxlcrtiv/model-ledger)](https://github.com/pxlcrtiv/model-ledger)
![Solidity 0.8.26](https://img.shields.io/badge/Solidity-0.8.26-363636?logo=solidity)
![Foundry](https://img.shields.io/badge/built%20with-Foundry-000000?logo=ethereum)
![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB?logo=python)

---

## The problem

Anyone can publish a model card on Hugging Face — and anyone can edit it later,
swap the weights, or repost the card under a different name. There is no
cryptographic record of *"this exact set of files was published by this person
at this time."* AI provenance is currently a matter of trust, not of proof.

## What this project does

ModelLedger is a tiny EVM registry plus a CLI that together give models
**verifiable provenance**:

1. **Manifest** — the CLI builds a canonical manifest of a model's files
   (path, size, sha256 of every file) — from a Hugging Face repo or a local
   directory. Sorted, deterministic, byte-exact.
2. **Register** — it sends `keccak256(canonical_manifest)` to a
   `ModelLedger` smart contract, with repo id, owner and timestamp.
3. **Verify** — anyone re-hashes the manifest locally (the CLI, the contract
   itself, or the web viewer) and compares it against the chain. Matching hash
   = the files are exactly what the owner registered. No oracle, no API key.

```
┌──────────────┐  sha256 per file   ┌────────────────────┐
│ HF Hub repo  │ ─────────────────► │ canonical manifest │
│ or local dir │    sorted entries  │ JSON               │
└──────────────┘                    └─────────┬──────────┘
                                              │ keccak256   (same bytes hashed
                                              ▼              in EVM via hashManifest)
┌──────────────┐   register(tx)   ┌────────────────────────┐
│ model-ledger │ ───────────────► │ ModelLedger · Sepolia  │
│ CLI / web    │ ◄─────────────── │ registry contract      │
└──────────────┘   verify (view)  └────────────────────────┘
```

The canonical manifest format is locked by **golden cross-language tests**:
`test/ModelLedger.t.sol` embeds the same fixture hash as `cli/tests/test_manifest.py`,
so Python and Solidity can never drift apart.

## Quickstart — 60 seconds on a local anvil chain

No testnet funds, no API keys — the whole flow runs locally:

```bash
# 1. anvil ships with Foundry
anvil

# 2. in another terminal:
cd cli && pip install -r requirements.txt
python -m model_ledger demo
```

Real output from a local run (this exact transcript was captured live):

```
── model-ledger demo ──────────────────────────────────────
reusing deployment 0xDc64a140Aa3E981100a9becA4E685f962f0cF6C9 (delete deployments/anvil.json to redeploy)
manifest (2 files, .../examples/demo-model):
  hash: 0xc6b50c4dcaeea06eaa85a10a7c26bb8faa0137b9f0928e13f344375f5efafca9
registered: tx 46980287ed0c35f78d2ec448c5b1b8c9f6458a0815788596b80baf64e3d6d0a6 (block 7)
verify:  VERIFIED ✓
  repoId           pxlcrtiv/demo-model
  owner            0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
  manifestHash     0xc6b50c4dcaeea06eaa85a10a7c26bb8faa0137b9f0928e13f344375f5efafca9
  metadataUri      -
  registeredAt     2026-08-23 21:57:48 UTC
  updatedAt        2026-08-23 21:57:48 UTC
  manifestVersion  1
total:   2 model(s) registered
── demo complete ──────────────────────────────────────────
contract address: 0xDc64a140Aa3E981100a9becA4E685f962f0cF6C9  (saved in deployments/anvil.json)
```

## The smart contract

`contracts/ModelLedger.sol` — zero dependencies, ~200 lines, no value held
by design. Per-model records are owner-controlled, so registration is cheap
and transfers are explicit.

| Function | Description |
|----------|-------------|
| `registerModel(repoId, manifestHash, metadataUri)` | Register a model (first time). Reverts on duplicates / empty input. |
| `updateManifest(repoId, newHash, newUri)` | Owner-only manifest update; bumps `manifestVersion`. |
| `transferOwnership(repoId, newOwner)` | Owner-only record transfer. |
| `verifyModel(repoId, candidateHash)` | `true` iff registered and hash matches. Unknown repo ⇒ `false`. |
| `verifyManifest(repoId, canonicalJson)` | Verify by re-hashing the manifest *on-chain*. |
| `hashManifest(canonicalJson)` | Pure helper — the same bytes hash identically in EVM and Python. |
| `getModel(repoId)` / `isRegistered` / `totalModels` / `repoIdAt` / `allRepoIds` | Read APIs. |

## Tests

```bash
forge test          # 18 tests: behaviors, events, fuzz, golden cross-language hash
pytest cli/tests/   # unit tests (hashing, sorting, local dir) + live anvil lifecycle
```

CI runs all three jobs on every push: **forge build + test (with `--sizes`)**, **CLI unit tests**, and a **full lifecycle e2e on a fresh anvil**.

## Deploy to Sepolia

1. Get a little SepoliaETH (testnet faucet) into a throwaway wallet.
2. Copy `.env.example` to `.env` and fill `PRIVATE_KEY`, `SEPOLIA_RPC_URL`, `ETHERSCAN_API_KEY`.
3. Deploy + verify with Foundry:

```bash
source .env
forge script script/Deploy.s.sol:DeployModelLedger \
  --rpc-url $SEPOLIA_RPC_URL --private-key $PRIVATE_KEY --broadcast

# verify on Etherscan (optional but nice)
forge verify-contract <ADDRESS> contracts/ModelLedger.sol:ModelLedger \
  --chain sepolia --etherscan-api-key $ETHERSCAN_API_KEY

# or deploy straight from the CLI
python -m model_ledger deploy --rpc $SEPOLIA_RPC_URL --key $PRIVATE_KEY
```

4. Register — the CLI auto-discovers the address from `deployments/sepolia.json`:

```bash
python -m model_ledger manifest --repo hf-internal-testing/tiny-random-distilbert
python -m model_ledger register hf-internal-testing/tiny-random-distilbert --hash 0x1b30bb…
```

> **Sepolia-only policy.** This is a demo-grade registry, not a token contract.
> Never point it at mainnet, never fund it beyond testnet ETH.

## CLI reference

```
python -m model_ledger <command> [options]

manifest --repo <hf-repo> | --local-dir <path>   build canonical manifest, print hash
register <repo> --hash 0x… | --manifest <file> [--uri …]
verify   <repo> --hash 0x… | --manifest <file>   check registration
get      <repo>                                  print on-chain record
list                                          all registered repo ids
update   <repo> --hash 0x… [--uri …]             owner-only manifest update
deploy   [--rpc …] [--key …]                     deploy registry, save deployments/<net>.json
demo      [--repo …]                             full local anvil end-to-end
```

Options come from flags or env: `MODEL_LEDGER_RPC_URL`, `MODEL_LEDGER_PRIVATE_KEY`,
`MODEL_LEDGER_CONTRACT`. Default RPC is `http://127.0.0.1:8545` (anvil).

## Web viewer

`web/index.html` — a zero-dependency, read-only viewer (ethers.js via CDN).
View calls only: it can never send a transaction.

```bash
python -m http.server 8000 --directory web
# open http://localhost:8000/?rpc=http://127.0.0.1:8545&address=<contract>&repo=pxlcrtiv/demo-model
```

## Trust model & security

- **What registration proves:** "this pubkey/fingerprint was registered for this repo id at this time, and updated at these times." Not "this code is safe."
- **Manifest hashing is client-side and canonical**: a verifier re-hashes the actual files — nothing is trusted except the chain's record.
- **The contract holds nothing**: no ETH, no ERC-20, no value transfer paths. Attack surface is a public append-only mapping.
- **Testnet-first**: Sepolia is the reference deployment; the demo runs on local anvil. See `SECURITY` section of the roadmap for the trust-model deep-dive.

## Repository layout

```
contracts/ModelLedger.sol   registry contract (zero-dependency)
script/Deploy.s.sol         forge deployment script
test/ModelLedger.t.sol      18 passing tests incl. golden cross-language hash
cli/model_ledger/           Python CLI (web3.py + huggingface_hub + click)
cli/tests/                  unit + live anvil integration tests
web/index.html              read-only ethers.js viewer
examples/demo-model/        tiny fake model for offline demos
deployments/                per-network deployed addresses (anvil/sepolia)
ROADMAP.md                  daily-commit plan & backlog
```

## Roadmap

See [ROADMAP.md](ROADMAP.md) — day-by-day plan, open backlog, and the golden-hash
maintenance rule. The repo is built for steady, meaningful daily commits.

## Contributing

Issues, PRs and demo ideas welcome. Before opening a PR: `forge fmt` +
`forge test` + `pytest cli/tests/` must pass; if you touch the manifest format,
update **both** golden fixtures in the same commit. See CONTRIBUTING rules in
[ROADMAP.md](ROADMAP.md).

## License

MIT — see [LICENSE](LICENSE).