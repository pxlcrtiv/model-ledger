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

