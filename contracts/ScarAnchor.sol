// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract ScarAnchor {
    event ScarAnchored(bytes32 indexed scarHash, string scarId, uint256 timestamp, address indexed operator);
    mapping(bytes32 => uint256) public anchoredAt;
    function anchor(bytes32 scarHash, string calldata scarId) external {
        require(anchoredAt[scarHash] == 0, "already anchored");
        anchoredAt[scarHash] = block.timestamp;
        emit ScarAnchored(scarHash, scarId, block.timestamp, msg.sender);
    }
}
