// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console2} from "forge-std/Script.sol";
import {ModelLedger} from "../contracts/ModelLedger.sol";

/// @notice Deploy ModelLedger to any network via:
///         forge script script/Deploy.s.sol:DeployModelLedger \
///           --rpc-url $SEPOLIA_RPC_URL --private-key $PRIVATE_KEY --broadcast
contract DeployModelLedger is Script {
    function run() external returns (ModelLedger ledger) {
        uint256 deployerKey = vm.envUint("PRIVATE_KEY");
        vm.startBroadcast(deployerKey);
        ledger = new ModelLedger();
        vm.stopBroadcast();

        console2.log("ModelLedger deployed at:", address(ledger));
        console2.log("Chain id:", block.chainid);
        console2.log("Gas used by constructor is minimal - the registry holds no value.");
    }
}
