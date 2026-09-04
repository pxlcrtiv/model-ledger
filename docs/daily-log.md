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


## 2026-08-27 — Daily entry: EIP-1167 clones: one registry logic, many instances

Minimal proxies (20 lines of bytecode) let every team deploy their own registry pointing at shared logic — cheap (a few thousand gas) and individually ownable. Great for 'registry per org, logic shared' designs. The canonical hash still lives per-instance.

> `grep -rni 'clone\|1167' contracts/ 2>/dev/null || echo 'ModelLedger deploys full contracts for now'`


## 2026-08-28 — Daily entry: EIP-712 typed signatures: off-chain consent, on-chain records

With EIP-712, the registry could accept signed metadata updates (the model owner signs a new manifest hash, any relayer submits it) — the classic 'gasless' pattern. `domainSeparator` + `hashStruct` must match exactly between signer and verifier; golden tests are the safety net.

> `cast sig 'verifyModelUpdate(bytes32,bytes32,uint256,bytes)'`


## 2026-08-29 — Daily entry: personal_sign vs typed data: never hand-roll signatures

Raw `personal_sign` of arbitrary bytes is how signature-replay bugs happen (users sign a 'message' that is actually a transaction). Prefer typed, domain-separated schemas (EIP-712) or EIP-191 versioned envelopes so a signature means exactly one thing.

> `cast sig 'claim(string,address,uint256)'`


## 2026-08-30 — Daily entry: Keepers vs cron: on-chain automation is a trust decision

Automated registry maintenance (heartbeat updates, expiry checks) can run off-chain (cron/launchd — like this very repo) or via keepers (Chainlink Automation). Off-chain is simpler and free; on-chain keepers are censorship-resistant. For a provenance registry, off-chain beats on-chain until trust questions are answered.

> `crontab -l 2>/dev/null | head -5`


## 2026-08-31 — Daily entry: EIP-2981: royalties for model NFTs, if you go that route

If model ownership ever tokenizes (memberships, licensing), EIP-2981 gives the registry a standard royalty interface — one function, `royaltyInfo`, that marketplaces read. It does not move money itself; it informs the marketplace. Standard > bespoke for anything other contracts will integrate.

> `cast sig 'royaltyInfo(uint256,uint256)(address,uint256)'`


## 2026-09-01 — Daily entry: Semver for artifacts: models are software too

MAJOR for architecture changes (weights incompatible), MINOR for behavior changes (new tokenizer, same arch), PATCH for retrains of the same config. Semantic versions make registry queries ('newest compatible v2') mechanical instead of tribal knowledge. Record the version in the manifest, not just the filename.

> `jq '.version' example/demo-model/manifest.json`


## 2026-09-02 — Daily entry: Hash trees: don't register a 2 GB file, register its tree root

For multi-file artifacts (weights + tokenizer + configs), hash each file and register the root of the tree. Verifying any subset of files is possible without the rest. This is how the registry scales from demo models to real checkpoints.

> `mlm manifest register --model example/demo-model --owner 0xYourAddress`


## 2026-09-03 — Daily entry: Cold vs warm slots: why the registry reads are cheap

First read of a storage slot costs 2100 gas (cold), subsequent 100 (warm). A CLI that reads the same record's fields back-to-back is naturally warm — but a dApp that re-queries per field pays cold repeatedly. Batch reads into one call/struct return where possible.

> `cast call <registry> 'getRecord(address,string)(string,bytes32,uint256,bool)' <owner> 'demo-model'`


## 2026-09-04 — Daily entry: .env discipline: keys are not code

The repo's `.env.example` lists every variable the deploy scripts need. Keep real keys out of git — a leaked `PRIVATE_KEY` in the registry repo compromises the *owner role of the registry itself*. `git log -p` is forever; rotate immediately if anything sensitive ever lands.

> `grep -rn 'PRIVATE_KEY\|SEPOLIA' .env.example`

