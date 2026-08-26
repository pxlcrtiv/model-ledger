# ModelLedger — daily log

> Maintained by `scripts/daily_update.py` (Daily Green automation) — one
> dated, non-empty registry/EVM best-practice entry per day, rotated from
> the pool in `scripts/tips_pool.json`. Pause by creating a `.daily-pause`
> file in the repo root, or unload the scheduler job (see README, Daily Green).


## 2026-08-23 — Daily entry: The admin key is the real attack surface

Once the registry is live, the only way to mutate it is the owner key. A single EOA owner is a single point of failure — consider a multisig or timelock for the registry admin role. Document the key-handling decision in the README so reviewers know the threat model.

> `cast call <registry> 'owner()(address)'`


## 2026-08-24 — Daily entry: Renouncing ownership is a governance decision, not a cleanup step

`renounceOwnership` permanently freezes the registry to append-only. That maximizes trust (nobody can mutate records) and removes your ability to fix bugs. Think of it as the 'mainnet immutable' moment — do it deliberately, with a planned feature freeze, not on a whim.

> `cast send <registry> 'renounceOwnership()' --from <owner>`


## 2026-08-25 — Daily entry: Proxies: the upgrade later you may never need

An upgradeable registry (EIP-1967 proxy) trades a little trust for future flexibility — but every proxy is a point of centralization and storage-layout discipline. For a provenance registry, immutability is often the *feature*; decide once, at design time, and document the decision.

> `grep -rn 'proxy\|upgrade' contracts/ docs/ 2>/dev/null || echo 'registry is deliberately immutable'`


## 2026-08-26 — Daily entry: CREATE2: deterministic deployment addresses

`CREATE2` lets you compute the registry address before it exists (salt + init code hash). Deterministic addresses make README links stable across redeploys and let dApps pre-approve the registry. Foundry: `computeCreate2Address` cheatcode or `cast create2` for tooling.

> `cast create2 --init-code $(forge inspect ModelLedger bytecode) --salt 0x0`

