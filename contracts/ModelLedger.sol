// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title ModelLedger
/// @notice On-chain provenance registry for machine-learning model artifacts.
/// @dev    Model authors register a cryptographic fingerprint (keccak256) of the
///         canonical manifest of their model's files. Anyone can re-hash the
///         manifest locally and compare it against the chain, so provenance of
///         a published model card can be verified in one call — no trusted
///         third party, no API key.
///
/// Canonical manifest hashing is defined in the Python CLI (`cli/`):
///   manifest = {"files": [{"path": ..., "sha256": ..., "size": ...}, ...]}
///   hash     = keccak256(utf-8 bytes of the manifest with sorted entries)
///
/// Security posture: testnet-first. This contract holds no value by design;
/// it is a public registry. Registering does not transfer anything.
contract ModelLedger {
    /// @notice A registered model and its provenance record.
    struct ModelRecord {
        /// Owner of the record — the registrar, transferable.
        address owner;
        /// keccak256 of the canonical manifest (see file header).
        bytes32 manifestHash;
        /// Hugging Face repo id, e.g. "black-forest-labs/FLUX.1-dev".
        string repoId;
        /// Optional URI pointing at the manifest / model card on IPFS or HTTPS.
        string metadataUri;
        /// block.timestamp of the initial registration.
        uint64 registeredAt;
        /// block.timestamp of the last manifest update.
        uint64 updatedAt;
        /// Monotonic version, bumped on every update. Starts at 1.
        uint64 manifestVersion;
    }

    /// repoId => provenance record.
    mapping(string => ModelRecord) private _records;

    /// Insertion-ordered list of all registered repo ids (for enumeration).
    string[] private _allRepoIds;

    // ------------------------------------------------------------------ errors

    error EmptyRepoId();
    error ZeroManifestHash();
    error AlreadyRegistered(string repoId);
    error NotRegistered(string repoId);
    error NotOwner(string repoId);
    error ZeroAddress();

    // ------------------------------------------------------------------ events

    /// @notice Emitted when a model is registered for the first time.
    event ModelRegistered(
        string indexed repoId,
        address indexed owner,
        bytes32 manifestHash,
        string metadataUri,
        uint64 registeredAt
    );

    /// @notice Emitted when an owner updates the manifest hash or metadata URI.
    event ModelUpdated(
        string indexed repoId,
        bytes32 manifestHash,
        string metadataUri,
        uint64 updatedAt,
        uint64 manifestVersion
    );

    /// @notice Emitted when record ownership is transferred.
    event OwnershipTransferred(
        string indexed repoId, address indexed previousOwner, address indexed newOwner
    );

    // --------------------------------------------------------------- registration

    /// @notice Register a model's artifact manifest fingerprint.
    /// @param repoId      Unique repo identifier, e.g. "org/model-name".
    /// @param manifestHash keccak256 of the canonical manifest (see `hashManifest`).
    /// @param metadataUri  Optional URI to the manifest or model card ("" allowed).
    /// @return registeredAt The block.timestamp of registration.
    /// @custom:reverts AlreadyRegistered if repoId is taken.
    function registerModel(
        string calldata repoId,
        bytes32 manifestHash,
        string calldata metadataUri
    ) external returns (uint64 registeredAt) {
        if (bytes(repoId).length == 0) revert EmptyRepoId();
        if (manifestHash == bytes32(0)) revert ZeroManifestHash();
        if (_records[repoId].owner != address(0)) revert AlreadyRegistered(repoId);

        ModelRecord storage rec = _records[repoId];
        rec.owner = msg.sender;
        rec.manifestHash = manifestHash;
        rec.repoId = repoId;
        rec.metadataUri = metadataUri;
        rec.registeredAt = uint64(block.timestamp);
        rec.updatedAt = rec.registeredAt;
        rec.manifestVersion = 1;
        _allRepoIds.push(repoId);

        emit ModelRegistered(repoId, msg.sender, manifestHash, metadataUri, rec.registeredAt);
        return rec.registeredAt;
    }

    /// @notice Update the manifest hash / metadata URI of a model you own.
    function updateManifest(
        string calldata repoId,
        bytes32 newManifestHash,
        string calldata newMetadataUri
    ) external {
        ModelRecord storage rec = _records[repoId];
        if (rec.owner == address(0)) revert NotRegistered(repoId);
        if (msg.sender != rec.owner) revert NotOwner(repoId);
        if (newManifestHash == bytes32(0)) revert ZeroManifestHash();

        rec.manifestHash = newManifestHash;
        rec.metadataUri = newMetadataUri;
        rec.updatedAt = uint64(block.timestamp);
        rec.manifestVersion += 1;

        emit ModelUpdated(
            repoId, newManifestHash, newMetadataUri, rec.updatedAt, rec.manifestVersion
        );
    }

    /// @notice Transfer record ownership (e.g. when a model changes maintainer).
    function transferOwnership(string calldata repoId, address newOwner) external {
        if (newOwner == address(0)) revert ZeroAddress();
        ModelRecord storage rec = _records[repoId];
        if (rec.owner == address(0)) revert NotRegistered(repoId);
        if (msg.sender != rec.owner) revert NotOwner(repoId);

        address previousOwner = rec.owner;
        rec.owner = newOwner;
        emit OwnershipTransferred(repoId, previousOwner, newOwner);
    }

    // ------------------------------------------------------------------ reads

    /// @notice Verify a candidate manifest hash for a repo id.
    /// @return verified True iff the model is registered AND its on-chain
    ///         manifest hash equals `candidateHash`. Unknown repos => false.
    /// @dev public (not external) so verifyManifest can call it internally —
    ///      external functions with calldata params cannot be called internally.
    function verifyModel(string calldata repoId, bytes32 candidateHash)
        public
        view
        returns (bool verified, ModelRecord memory record)
    {
        ModelRecord storage rec = _records[repoId];
        if (rec.owner == address(0)) return (false, rec);
        return (rec.manifestHash == candidateHash, rec);
    }

    /// @notice Verify a full canonical manifest string against the chain.
    ///         This is the "trustless" check: hash the manifest yourself,
    ///         compare on-chain — no off-chain oracle involved.
    function verifyManifest(string calldata repoId, string calldata canonicalManifest)
        external
        view
        returns (bool verified, ModelRecord memory record)
    {
        return verifyModel(repoId, keccak256(bytes(canonicalManifest)));
    }

    /// @notice Pure helper mirroring the CLI's manifest hashing, so the same
    ///         bytes hash identically in EVM and Python.
    function hashManifest(string calldata canonicalManifest) external pure returns (bytes32) {
        return keccak256(bytes(canonicalManifest));
    }

    /// @notice Full record for a repo id. Reverts if not registered.
    function getModel(string calldata repoId) external view returns (ModelRecord memory) {
        ModelRecord storage rec = _records[repoId];
        if (rec.owner == address(0)) revert NotRegistered(repoId);
        return rec;
    }

    /// @notice True if repoId is registered.
    function isRegistered(string calldata repoId) external view returns (bool) {
        return _records[repoId].owner != address(0);
    }

    /// @notice Number of registered models.
    function totalModels() external view returns (uint256) {
        return _allRepoIds.length;
    }

    /// @notice i-th registered repo id (insertion order).
    function repoIdAt(uint256 i) external view returns (string memory) {
        return _allRepoIds[i];
    }

    /// @notice All registered repo ids (small registries only — O(n) copy).
    function allRepoIds() external view returns (string[] memory) {
        return _allRepoIds;
    }
}
