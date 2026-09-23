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


## 2026-09-05 — Daily entry: anvil: the registry's local playground

`anvil` spins up a local chain with pre-funded accounts in one command. It is how the CLI's `demo` command shows end-to-end register -> verify flows without any faucet — and exactly how the README's live transcript was produced. Local-first verification beats testnet-first for every iteration.

> `anvil && mlm demo`


## 2026-09-06 — Daily entry: chisel: REPL your way through storage layouts

Foundry's `chisel` gives an interactive Solidity REPL — instant experiments with struct packing, ABI encoding, and hashing before they become contract code. For registry record layouts, fifteen minutes in chisel beats three deploy-test cycles.

> `chisel`


## 2026-09-07 — Daily entry: The verification loop: register, forget, verify

The strongest demo of a provenance registry is the 'cold verify': delete local state, re-fetch the manifest from the registry, and prove the hash matches the artifact. If that works from another machine, the system is doing its job. This is the test to show a skeptical reviewer.

> `mlm verify --model example/demo-model && sha256sum example/demo-model/manifest.json`


## 2026-09-08 — Daily entry: Document the demo so the demo documents you

The README's live transcript (real anvil output, real hashes) is the highest-signal artifact for anyone evaluating the repo — it proves the pipeline works without trusting a word of prose. Keep transcripts regenerated when the CLI changes; stale transcripts are worse than none.

> `mlm demo 2>&1 | tee docs/demo-transcript.txt`


## 2026-09-09 — Daily entry: A little green every day beats a big bang

This very file is the pattern: one small, real, dated contribution per day compounds into a contribution history that says 'this person ships constantly'. The registry's ROADMAP doles the backlog into day-sized chunks for the same reason — activity that recruiters can see is activity that pays.

> `git log --oneline --since=7.days | wc -l`


## 2026-09-10 — Daily entry: A model registry is a hash ledger, not a file server

The whole point of ModelLedger is that the artifact lives anywhere (HF Hub, S3, your laptop) and the chain stores only its fingerprint: manifest hash + metadata + owner. Keep `sha256` of the manifest as the record key — it is cryptographically stable across languages, which is exactly why the golden cross-language tests lock it in Solidity and Python.

> `mlm manifest register --model example/demo-model --owner 0xYourAddress`


## 2026-09-11 — Daily entry: Why sha256 and not keccak256 for content

keccak256 is the EVM's native hash and is great for storage keys, but sha256 is the universal content-addressing standard (IPFS, Git, GCS) — the same manifest hashes identically in Python, JS, and Go. ModelLedger deliberately uses sha256 for artifact integrity and keccak256 for EVM addressing. Mixing them up is a classic cross-language footgun; the golden tests exist to catch exactly that.

> `python -c "import hashlib; print(hashlib.sha256(b'model').hexdigest())"`


## 2026-09-12 — Daily entry: Manifest = the reproducibility contract

A good manifest pins: model name, version, framework, architecture, weights hash, dataset(s) used, license, and training config. Someone with the manifest can rebuild the artifact close enough to verify integrity — that is what makes a registry trustworthy instead of a directory.

> `mlm manifest --help`


## 2026-09-13 — Daily entry: Register the manifest, not the blob

Hashing a multi-GB checkpoint on-chain is absurd (and unpayable). Hash the *manifest*, which itself contains the blob hashes — a Merkle-trie style chain of trust: record -> manifest -> weights. Registration cost stays constant regardless of model size.

> `mlm manifest register --model example/demo-model --owner 0xYourAddress`


## 2026-09-14 — Daily entry: Events are the free database of the registry

Indexing `RecordRegistered(address owner, string modelId, bytes32 manifestHash, ...)` topics is how explorers, UIs, and bots learn about records — cheaper and more reliable than reading storage. If your registry frontend ever breaks, the events are the fallback source of truth.

> `cast logs --address <registry> 'RecordRegistered(address,string,bytes32,uint256,uint256)'`


## 2026-09-15 — Daily entry: Struct packing: three uint256 records can cost 3x the gas of one packed

Storage writes cost 20k gas per fresh slot. Order struct fields fat-to-thin (uint256, address, bytes32, then pack uints together) so related values share slots. In a registry record, `timestamp`, `owner`, and version fit naturally — measure with `forge snapshot` before and after.

> `forge snapshot --diff`


## 2026-09-16 — Daily entry: Revert loudly, return quietly

Registry reads should revert with a reason string (`getRecord` on an unknown id) so callers can't treat 'not found' as 'zero record'. External-facing helper functions returning bools hide failures in downstream integrations. Foundry tests should assert the exact revert reason.

> `forge test --match-test testRevertUnknownRecord -vvv`


## 2026-09-17 — Daily entry: Ownable without the ceremony

ModelLedger's registry is zero-dependency: `onlyOwner` is a modifier, not an OpenZeppelin import. That is a deliberate call — fewer deps means faster CI, smaller bytecode, and no supply-chain surface. The trade-off is you hand-audit the two lines that make up the pattern.

> `cat contracts/ModelLedger.sol | grep -n 'onlyOwner\|owner' | head`


## 2026-09-18 — Daily entry: Append-only registries win trust

Letting anyone overwrite a model record destroys provenance — the record you verified yesterday is silently different today. Design for append-and-supersede: new versions create new records, old ones stay immutable and verifiable. Supersession (pointers from old to new) is a feature, mutation is a bug.

> `mlm list --address <registry>`


## 2026-09-19 — Daily entry: Metadata schema versioning: v1 records never die

The moment you change the manifest JSON shape, old records must still parse and verify. Version the schema inside the manifest (`"schema": "model-ledger/v1"`) and keep a decoder per version in the CLI. Breaking parsing = breaking every past verification.

> `jq '.schema' example/demo-model/manifest.json`


## 2026-09-20 — Daily entry: HF Hub hashes are free integrity anchors

Hugging Face exposes `sha256` metadata for every file in a repo. ModelLedger reads that metadata without downloading the weights — a lightning-fast, offline-friendly way to build the manifest the registry will hold.

> `mlm manifest register --model gpt2 --from-hf`


## 2026-09-21 — Daily entry: Pin, pin, pin: reproducibility starts at the dataset

A model is a function of its data. If the dataset revision is unpinned, the checkpoint cannot be reproduced, and the registry record is theater. Store dataset name + revision/commit in the manifest, and prefer dataset-dedicated revisions over 'latest'.

> `mlm manifest --help  # dataset fields`


## 2026-09-22 — Daily entry: License fields belong in the manifest, not in the README

License drift is a real legal risk: a model re-released under a stricter license invalidates downstream use. Pin the license string in the manifest at registration time so the record is the audit trail, and re-register on license changes instead of editing prose.

> `jq '.license' example/demo-model/manifest.json`


## 2026-09-23 — Daily entry: Benchmarks without hardware context are noise

Registering 'accuracy 0.912' means nothing unless the manifest records hardware, precision, batch size, and dataset split. Benchmark values are part of the reproducibility contract, not decoration. ModelLedger records them as structured metadata so comparisons stay honest.

> `mlm verify --model example/demo-model`

