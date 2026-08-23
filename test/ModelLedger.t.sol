// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test, console2} from "forge-std/Test.sol";
import {ModelLedger} from "../contracts/ModelLedger.sol";

/// @notice Behavioral tests for the ModelLedger registry.
contract ModelLedgerTest is Test {
    ModelLedger internal ledger;
    address internal alice = makeAddr("alice");
    address internal bob = makeAddr("bob");

    bytes32 internal constant MANIFEST = keccak256("some-manifest-bytes");
    string internal constant REPO = "alice/first-model";
    string internal constant URI = "ipfs://QmDemo";

    /// @dev Golden cross-language fixture: the canonical manifest of
    ///      examples/demo-model as produced by cli/model_ledger/manifest.py.
    ///      If this hash ever stops matching, the CLI and the contract
    ///      disagree about what "the manifest hash" means — fail loudly.
    string internal constant GOLDEN_CANONICAL =
        '{"files":[{"path":"README.md","sha256":"3c70040eaecfe1da5509a6b6f0c2b265254a26558f0206339a49f7c6e53e786e","size":205},{"path":"config.json","sha256":"985e3e4faf1496d31c27823ad8a90848c6bef6b72ff363c1e66b48b1e0dd8e1b","size":158}]}';
    bytes32 internal constant GOLDEN_HASH =
        0xc6b50c4dcaeea06eaa85a10a7c26bb8faa0137b9f0928e13f344375f5efafca9;

    function setUp() public {
        ledger = new ModelLedger();
    }

    function _registerAs(address who, string memory repo, bytes32 hash, string memory uri)
        internal
    {
        vm.prank(who);
        ledger.registerModel(repo, hash, uri);
    }

    // ------------------------------------------------------------ registration

    function test_RegisterModel() public {
        vm.prank(alice);
        uint64 registeredAt = ledger.registerModel(REPO, MANIFEST, URI);

        assertEq(registeredAt, uint64(block.timestamp));
        ModelLedger.ModelRecord memory rec = ledger.getModel(REPO);
        assertEq(rec.owner, alice);
        assertEq(rec.manifestHash, MANIFEST);
        assertEq(rec.repoId, REPO);
        assertEq(rec.metadataUri, URI);
        assertEq(rec.registeredAt, uint64(block.timestamp));
        assertEq(rec.updatedAt, uint64(block.timestamp));
        assertEq(rec.manifestVersion, 1);
        assertTrue(ledger.isRegistered(REPO));
        assertEq(ledger.totalModels(), 1);
        assertEq(ledger.repoIdAt(0), REPO);
    }

    function test_RegisterEmitsEvent() public {
        vm.expectEmit(true, true, true, true);
        emit ModelLedger.ModelRegistered(REPO, alice, MANIFEST, URI, uint64(block.timestamp));
        vm.prank(alice);
        ledger.registerModel(REPO, MANIFEST, URI);
    }

    function test_RevertWhen_AlreadyRegistered() public {
        _registerAs(alice, REPO, MANIFEST, URI);
        vm.expectRevert(abi.encodeWithSelector(ModelLedger.AlreadyRegistered.selector, REPO));
        vm.prank(bob);
        ledger.registerModel(REPO, MANIFEST, URI);
    }

    function test_RevertWhen_EmptyRepoId() public {
        vm.expectRevert(ModelLedger.EmptyRepoId.selector);
        ledger.registerModel("", MANIFEST, "");
    }

    function test_RevertWhen_ZeroManifestHash() public {
        vm.expectRevert(ModelLedger.ZeroManifestHash.selector);
        ledger.registerModel(REPO, bytes32(0), "");
    }

    // ------------------------------------------------------------ verification

    function test_VerifyModel_MatchingAndMismatching() public {
        _registerAs(alice, REPO, MANIFEST, "");
        (bool ok1, ModelLedger.ModelRecord memory rec) = ledger.verifyModel(REPO, MANIFEST);
        assertTrue(ok1);
        assertEq(rec.owner, alice);

        (bool ok2,) = ledger.verifyModel(REPO, keccak256("tampered"));
        assertFalse(ok2);
    }

    function test_VerifyModel_UnknownRepoReturnsFalse() public {
        (bool ok,) = ledger.verifyModel("nobody/ghost", MANIFEST);
        assertFalse(ok);
    }

    function test_VerifyManifest_GoldenCrossLanguageHash() public {
        bytes32 h = ledger.hashManifest(GOLDEN_CANONICAL);
        assertEq(h, GOLDEN_HASH, "CLI and contract manifest hashing diverged");
        _registerAs(alice, REPO, GOLDEN_HASH, "");
        (bool ok,) = ledger.verifyManifest(REPO, GOLDEN_CANONICAL);
        assertTrue(ok);
        (bool bad,) = ledger.verifyManifest(REPO, '{"files":[]}');
        assertFalse(bad);
    }

    // ----------------------------------------------------------------- updates

    function test_UpdateManifest_OnlyOwner() public {
        _registerAs(alice, REPO, MANIFEST, URI);
        bytes32 v2 = keccak256("v2");
        vm.prank(alice);
        ledger.updateManifest(REPO, v2, "ipfs://QmNew");

        ModelLedger.ModelRecord memory rec = ledger.getModel(REPO);
        assertEq(rec.manifestHash, v2);
        assertEq(rec.metadataUri, "ipfs://QmNew");
        assertEq(rec.manifestVersion, 2);
        (bool ok,) = ledger.verifyModel(REPO, v2);
        assertTrue(ok);
    }

    function test_UpdateManifest_RevertsForNonOwner() public {
        _registerAs(alice, REPO, MANIFEST, "");
        vm.expectRevert(abi.encodeWithSelector(ModelLedger.NotOwner.selector, REPO));
        vm.prank(bob);
        ledger.updateManifest(REPO, keccak256("evil"), "");
    }

    function test_UpdateManifest_RevertsWhenNotRegistered() public {
        vm.expectRevert(abi.encodeWithSelector(ModelLedger.NotRegistered.selector, REPO));
        ledger.updateManifest(REPO, MANIFEST, "");
    }

    // ------------------------------------------------------- ownership transfer

    function test_TransferOwnership() public {
        _registerAs(alice, REPO, MANIFEST, "");
        vm.prank(alice);
        ledger.transferOwnership(REPO, bob);
        assertEq(ledger.getModel(REPO).owner, bob);

        vm.prank(bob);
        ledger.updateManifest(REPO, keccak256("v2"), "");

        vm.expectRevert(abi.encodeWithSelector(ModelLedger.NotOwner.selector, REPO));
        vm.prank(alice);
        ledger.updateManifest(REPO, keccak256("v3"), "");
    }

    function test_TransferOwnership_RevertsZeroAddress() public {
        _registerAs(alice, REPO, MANIFEST, "");
        vm.expectRevert(ModelLedger.ZeroAddress.selector);
        vm.prank(alice);
        ledger.transferOwnership(REPO, address(0));
    }

    // ------------------------------------------------------------------- reads

    function test_GetModel_RevertsWhenMissing() public {
        vm.expectRevert(abi.encodeWithSelector(ModelLedger.NotRegistered.selector, REPO));
        ledger.getModel(REPO);
    }

    function test_AllRepoIds() public {
        _registerAs(alice, "a/one", MANIFEST, "");
        _registerAs(bob, "b/two", MANIFEST, "");
        string[] memory ids = ledger.allRepoIds();
        assertEq(ids.length, 2);
        assertEq(ids[0], "a/one");
        assertEq(ids[1], "b/two");
    }

    function test_RepoIdAt_BoundsCheck() public {
        _registerAs(alice, "a/one", MANIFEST, "");
        vm.expectRevert();
        ledger.repoIdAt(1);
    }

    // -------------------------------------------------------------------- fuzz

    function testFuzz_RegisterVerifyRoundtrip(string calldata repoId, bytes32 hash) public {
        vm.assume(bytes(repoId).length > 0);
        vm.assume(bytes(repoId).length <= 64);
        vm.assume(hash != bytes32(0)); // contract rejects zero hash by design
        _registerAs(alice, repoId, hash, "");
        (bool ok, ModelLedger.ModelRecord memory rec) = ledger.verifyModel(repoId, hash);
        assertTrue(ok);
        assertEq(rec.owner, alice);
    }

    function testFuzz_DuplicateRegistrationAlwaysReverts(string calldata repoId) public {
        vm.assume(bytes(repoId).length > 0);
        _registerAs(alice, repoId, MANIFEST, "");
        vm.expectRevert(abi.encodeWithSelector(ModelLedger.AlreadyRegistered.selector, repoId));
        vm.prank(bob);
        ledger.registerModel(repoId, MANIFEST, "");
    }
}
