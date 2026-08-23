# ModelLedger — Roadmap (daily-commit plan)

This file is the working plan for keeping ModelLedger useful (and the GitHub
history bar green). The status table is updated as work lands. Each day gets
at least one commit; if a feature day stalls, land a docs/tests/refactor
commit instead — the bar counts commits.

## Day plan

| Day | Scope | Status |
|-----|-------|--------|
| D1  | Foundry scaffold + `ModelLedger.sol` (registry: owner, manifestHash, repoId, metadataUri, timestamps, version) | ✅ shipped in initial version |
| D2  | Forge tests (register/verify/update/transfer/fuzz + golden cross-language hash) — `forge test` green | ✅ 18/18 passing |
| D3  | Deploy to Sepolia via `forge script` + optional Etherscan verification + live tx link in README | ⏳ needs a funded test wallet (`PRIVATE_KEY` in `.env`) |
| D4  | Python CLI: HF manifest hashing + `register` | ✅ shipped (manifest, register, verify, get, list, update, deploy, demo) |
| D5  | `verify` flow + README with live demo transcript | ✅ shipped (this README) |
| D6  | End-to-end test script + CI badge (GitHub Actions) | ✅ shipped (3 CI jobs) |
| D7  | Demo GIF (real tx) + launch: Show HN + r/ethereum draft | ⏳ next |
| D8+ | Backlog: web viewer polish, Etherscan block-explorer links in CLI, HF Space demo, `--repo` register convenience flag, indexer stats page | open |

## Backlog ideas (pick one per day)

- [ ] CLI: `register --repo` convenience (manifest + register in one call)
- [ ] CLI: print a sepolia.etherscan.io tx link after register
- [ ] Web viewer: prefill from `?repo=&address=&rpc=` (already supported) + link out to Etherscan
- [ ] Contract: `findByManifestHash(bytes32)` reverse lookup + tests
- [ ] Contract: per-owner counter + `modelsOf(address)` enumeration
- [ ] Docs: architecture deep-dive post (canonical manifest format spec v1)
- [ ] Docs: attack-surface / trust-model write-up
- [ ] CI: add slither static analysis job (slither-analyzer is in the dev env)
- [ ] Demo: GIF of a real Sepolia registration + verification (needs D3 first)
- [ ] HF Space: Gradio viewer calling the Sepolia registry (needs D3 first)

## Rules

- Every commit is meaningful: code, tests, docs, or examples — never empty.
- The canonical manifest format is a *contract*: if you change
  `cli/model_ledger/manifest.py`, update the golden hash in
  `test/ModelLedger.t.sol` **in the same commit** (the test is the guard).
- Sepolia-only policy: no mainnet funds, no mainnet deployment, ever.