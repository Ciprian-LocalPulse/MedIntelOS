// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title MedIntelOS Governance (Multisig + Timelock)
 * @author MedIntelOS Contributors
 * @notice Replaces single-EOA `owner` control on
 *         `MedIntelOSConsentManager` and `MedIntelOSAuditLedger` with an
 *         N-of-M multisig subject to a mandatory timelock delay.
 *
 * @dev Design, not a claim of completeness:
 *   - This is intentionally minimal (propose / approve / execute / cancel)
 *     rather than a re-implementation of a full governance framework. It
 *     covers milestone 0.8.0 of docs/ROADMAP.md: "Multisig + timelock for
 *     administrative functions."
 *   - Deploy this contract, then transfer `owner` on both
 *     `MedIntelOSConsentManager` and `MedIntelOSAuditLedger` to this
 *     contract's address (see docs/DEPLOYMENT.md). Every `onlyOwner` call on
 *     those contracts then requires signer threshold + timelock.
 *   - Signer set changes go through the same propose/approve/execute/timelock
 *     path as any other action — there is no separate, faster path to add or
 *     remove signers.
 *   - This contract does NOT itself establish legal governance authority,
 *     key custody procedures, or incident response. Those remain documented
 *     operator responsibilities (see docs/GOVERNANCE.md).
 *   - An external security audit of this contract, tracked in
 *     docs/CONTRACT_AUDIT_CHECKLIST.md, is still required before any
 *     non-testnet deployment. Writing this contract does not satisfy that
 *     requirement.
 */
contract MedIntelOSGovernance {
    // --------------------------------------------------------
    // Types
    // --------------------------------------------------------

    struct Transaction {
        address target;
        uint256 value;
        bytes data;
        uint256 approvals;
        uint256 proposedAt;
        uint256 executableAt; // 0 until threshold reached
        bool executed;
        bool cancelled;
    }

    // --------------------------------------------------------
    // State
    // --------------------------------------------------------

    mapping(address => bool) public isSigner;
    address[] public signers;
    uint256 public threshold;      // approvals required to start the timelock
    uint256 public timelockDelay;  // seconds between threshold-reached and executable

    mapping(uint256 => Transaction) public transactions;
    mapping(uint256 => mapping(address => bool)) public hasApproved;
    uint256 public transactionCount;

    // --------------------------------------------------------
    // Events
    // --------------------------------------------------------

    event TransactionProposed(uint256 indexed txId, address indexed proposer, address target);
    event TransactionApproved(uint256 indexed txId, address indexed signer, uint256 approvals);
    event TransactionThresholdReached(uint256 indexed txId, uint256 executableAt);
    event TransactionExecuted(uint256 indexed txId);
    event TransactionCancelled(uint256 indexed txId, address indexed canceller);
    event SignerAdded(address indexed signer);
    event SignerRemoved(address indexed signer);
    event ThresholdChanged(uint256 newThreshold);
    event TimelockDelayChanged(uint256 newDelay);

    // --------------------------------------------------------
    // Modifiers
    // --------------------------------------------------------

    modifier onlySigner() {
        require(isSigner[msg.sender], "Governance: caller is not a signer");
        _;
    }

    modifier onlySelf() {
        require(msg.sender == address(this), "Governance: must go through propose/approve/execute");
        _;
    }

    modifier txExists(uint256 txId) {
        require(txId < transactionCount, "Governance: unknown transaction");
        _;
    }

    // --------------------------------------------------------
    // Constructor
    // --------------------------------------------------------

    /**
     * @param _signers Initial signer set (deduplicated, non-zero addresses)
     * @param _threshold Approvals required, 1 <= threshold <= _signers.length
     * @param _timelockDelay Minimum seconds between threshold and execution
     */
    constructor(address[] memory _signers, uint256 _threshold, uint256 _timelockDelay) {
        require(_signers.length > 0, "Governance: no signers");
        require(_threshold > 0 && _threshold <= _signers.length, "Governance: invalid threshold");

        for (uint256 i = 0; i < _signers.length; i++) {
            address signer = _signers[i];
            require(signer != address(0), "Governance: zero address signer");
            require(!isSigner[signer], "Governance: duplicate signer");
            isSigner[signer] = true;
            signers.push(signer);
            emit SignerAdded(signer);
        }

        threshold = _threshold;
        timelockDelay = _timelockDelay;
        emit ThresholdChanged(_threshold);
        emit TimelockDelayChanged(_timelockDelay);
    }

    // --------------------------------------------------------
    // Propose / Approve / Execute / Cancel
    // --------------------------------------------------------

    /**
     * @notice Propose a call to be executed by this contract once approved
     *         and the timelock has elapsed. Proposing counts as approving.
     */
    function propose(address target, uint256 value, bytes calldata data)
        external
        onlySigner
        returns (uint256 txId)
    {
        require(target != address(0), "Governance: zero target");

        txId = transactionCount++;
        Transaction storage t = transactions[txId];
        t.target = target;
        t.value = value;
        t.data = data;
        t.proposedAt = block.timestamp;

        emit TransactionProposed(txId, msg.sender, target);
        _approve(txId, msg.sender);
    }

    /// @notice Approve a pending transaction. Idempotent per signer.
    function approve(uint256 txId) external onlySigner txExists(txId) {
        Transaction storage t = transactions[txId];
        require(!t.executed, "Governance: already executed");
        require(!t.cancelled, "Governance: cancelled");
        _approve(txId, msg.sender);
    }

    /// @notice Revoke a not-yet-executed approval before the timelock starts.
    function revokeApproval(uint256 txId) external onlySigner txExists(txId) {
        Transaction storage t = transactions[txId];
        require(!t.executed, "Governance: already executed");
        require(t.executableAt == 0, "Governance: threshold already reached, cannot revoke");
        require(hasApproved[txId][msg.sender], "Governance: not approved by caller");

        hasApproved[txId][msg.sender] = false;
        t.approvals -= 1;
    }

    /// @notice Execute a transaction once threshold + timelock have both passed.
    function execute(uint256 txId) external onlySigner txExists(txId) {
        Transaction storage t = transactions[txId];
        require(!t.executed, "Governance: already executed");
        require(!t.cancelled, "Governance: cancelled");
        require(t.executableAt != 0, "Governance: threshold not reached");
        require(block.timestamp >= t.executableAt, "Governance: timelock not elapsed");

        t.executed = true;
        (bool success, ) = t.target.call{value: t.value}(t.data);
        require(success, "Governance: call reverted");

        emit TransactionExecuted(txId);
    }

    /// @notice Cancel a pending (not yet executed) transaction. Requires the
    ///         same signer threshold as approval, expressed as re-approving
    ///         cancellation is out of scope for this minimal contract, so any
    ///         single signer may cancel their own proposal before threshold,
    ///         and full governance (via execute -> cancelTransaction) can
    ///         cancel afterward.
    function cancelOwnProposal(uint256 txId) external txExists(txId) {
        Transaction storage t = transactions[txId];
        require(!t.executed, "Governance: already executed");
        require(t.executableAt == 0, "Governance: threshold already reached, use governance cancel");
        require(hasApproved[txId][msg.sender], "Governance: not the proposer or an approver");
        t.cancelled = true;
        emit TransactionCancelled(txId, msg.sender);
    }

    /// @dev Governance-gated cancel, reachable only via propose/approve/execute
    ///      targeting this contract itself (self-call pattern), matching how
    ///      signer/threshold/delay changes are also self-gated below.
    function cancelTransaction(uint256 txId) external onlySelf txExists(txId) {
        Transaction storage t = transactions[txId];
        require(!t.executed, "Governance: already executed");
        t.cancelled = true;
        emit TransactionCancelled(txId, address(this));
    }

    function _approve(uint256 txId, address signer) internal {
        if (hasApproved[txId][signer]) {
            return;
        }
        hasApproved[txId][signer] = true;

        Transaction storage t = transactions[txId];
        t.approvals += 1;
        emit TransactionApproved(txId, signer, t.approvals);

        if (t.approvals >= threshold && t.executableAt == 0) {
            t.executableAt = block.timestamp + timelockDelay;
            emit TransactionThresholdReached(txId, t.executableAt);
        }
    }

    // --------------------------------------------------------
    // Self-governed configuration changes
    // --------------------------------------------------------
    // These functions can only be called by this contract calling itself,
    // i.e. only via a proposal that itself went through the full
    // propose/approve/execute/timelock path. There is no admin shortcut.

    function addSigner(address signer) external onlySelf {
        require(signer != address(0), "Governance: zero address");
        require(!isSigner[signer], "Governance: already a signer");
        isSigner[signer] = true;
        signers.push(signer);
        emit SignerAdded(signer);
    }

    function removeSigner(address signer) external onlySelf {
        require(isSigner[signer], "Governance: not a signer");
        require(signers.length - 1 >= threshold, "Governance: would break threshold");
        isSigner[signer] = false;
        for (uint256 i = 0; i < signers.length; i++) {
            if (signers[i] == signer) {
                signers[i] = signers[signers.length - 1];
                signers.pop();
                break;
            }
        }
        emit SignerRemoved(signer);
    }

    function setThreshold(uint256 newThreshold) external onlySelf {
        require(newThreshold > 0 && newThreshold <= signers.length, "Governance: invalid threshold");
        threshold = newThreshold;
        emit ThresholdChanged(newThreshold);
    }

    function setTimelockDelay(uint256 newDelay) external onlySelf {
        timelockDelay = newDelay;
        emit TimelockDelayChanged(newDelay);
    }

    // --------------------------------------------------------
    // Views
    // --------------------------------------------------------

    function getSigners() external view returns (address[] memory) {
        return signers;
    }

    function getTransaction(uint256 txId) external view txExists(txId) returns (Transaction memory) {
        return transactions[txId];
    }

    receive() external payable {}
}
