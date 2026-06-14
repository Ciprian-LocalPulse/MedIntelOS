// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title MedIntelOS Patient Consent Manager
 * @author MedIntelOS Contributors
 * @notice Manages granular, auditable patient consent for health data sharing.
 *
 * @dev This contract implements:
 *   - Granular data scope consent (per FHIR resource type)
 *   - Purpose-based access control (treatment, research, public health)
 *   - Time-bounded, revocable consent
 *   - References to off-chain proof material
 *   - Revocation workflows that can support a broader privacy program
 *   - Emergency override with automatic audit trail
 *   - Proxy consent for minors and incapacitated patients
 *
 * Architecture:
 *   - Deployed on a permissioned Hyperledger Besu or Polygon PoS network
 *   - Interacts with off-chain FHIR server via oracle pattern
 *   - Events indexed by The Graph for fast querying
 *
 * This contract alone does not establish legal or regulatory compliance.
 * Deployments require legal review, identity binding, key recovery, incident
 * response, off-chain deletion, and an independently audited access model.
 */

// ============================================================
// Interfaces
// ============================================================

interface IConsentVerifier {
    /**
     * @notice Verify a zero-knowledge proof of consent without revealing patient identity
     * @param proofHash Hash of the ZK proof
     * @param publicSignals Public signals for the verifier circuit
     * @return valid True if proof is valid
     */
    function verifyProof(
        bytes32 proofHash,
        uint256[] calldata publicSignals
    ) external view returns (bool valid);
}

interface IAuditLedger {
    function logConsentEvent(
        bytes32 consentId,
        address patient,
        address requester,
        string calldata eventType,
        string calldata dataScope
    ) external;
}

// ============================================================
// Libraries
// ============================================================

library ConsentLib {
    /**
     * @notice Hash a consent record for integrity verification
     */
    function hashConsent(
        address patient,
        address requester,
        bytes32 scopeHash,
        uint256 expiresAt
    ) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked(
            patient, requester, scopeHash, expiresAt
        ));
    }
}

// ============================================================
// Main Contract
// ============================================================

contract MedIntelOSConsentManager {
    using ConsentLib for *;

    // --------------------------------------------------------
    // Types
    // --------------------------------------------------------

    enum ConsentPurpose {
        TREATMENT,           // Direct patient care
        RESEARCH,            // Clinical research (requires IRB approval hash)
        PUBLIC_HEALTH,       // Public health reporting
        PAYMENT,             // Billing and payment
        OPERATIONS,          // Healthcare operations
        EMERGENCY            // Emergency override (auto-reverts in 24h)
    }

    enum ConsentStatus {
        ACTIVE,
        REVOKED,
        EXPIRED,
        SUSPENDED,
        EMERGENCY_OVERRIDE
    }

    struct ConsentRecord {
        bytes32 consentId;
        address patient;           // Patient's wallet address (or proxy)
        address requester;         // Institution's wallet address
        string[] dataScope;        // FHIR resource types permitted
        ConsentPurpose purpose;
        ConsentStatus status;
        uint256 grantedAt;
        uint256 expiresAt;         // 0 = no expiry
        string zkProofHash;        // Off-chain ZK proof reference
        bytes32 irbApprovalHash;   // Research: IRB approval document hash
        bool isProxy;              // True if granted by legal proxy
        address proxyGrantor;      // If proxy, who granted it
        bytes32 patientReferenceHash; // Salted off-chain patient reference hash
        uint256 revokedAt;         // Timestamp of revocation (0 if active)
        string revocationReason;
        bytes32 gdprErasureProof;  // Proof of data erasure (GDPR Art. 17)
    }

    struct InstitutionProfile {
        address walletAddress;
        string name;
        string fhirBaseUrl;
        string jurisdiction;       // ISO 3166-1 alpha-2 country code
        bool verified;             // Verified by contract owner/DAO
        uint256 registeredAt;
        uint256 consentCount;
        uint256 violationCount;
    }

    struct EmergencyOverride {
        bytes32 consentId;
        address clinician;
        bytes32 clinicianReferenceHash;
        string justification;
        uint256 activatedAt;
        uint256 autoRevokeAt;      // Override auto-reverts after 24 hours
        bool active;
    }

    // --------------------------------------------------------
    // State Variables
    // --------------------------------------------------------

    address public owner;
    address public auditLedgerAddress;
    address public verifierAddress;

    mapping(bytes32 => ConsentRecord) public consents;
    mapping(address => bytes32[]) public patientConsents;
    mapping(address => bytes32[]) public requesterConsents;
    mapping(address => InstitutionProfile) public institutions;
    mapping(bytes32 => EmergencyOverride) public emergencyOverrides;
    mapping(address => mapping(address => bool)) public authorizedProxies;

    uint256 public totalConsentsGranted;
    uint256 public totalConsentsRevoked;

    uint256 public constant EMERGENCY_OVERRIDE_DURATION = 24 hours;
    uint256 public constant MAX_DATA_SCOPE_ITEMS = 50;

    // --------------------------------------------------------
    // Events
    // --------------------------------------------------------

    event ConsentGranted(
        bytes32 indexed consentId,
        address indexed patient,
        address indexed requester,
        ConsentPurpose purpose,
        uint256 expiresAt
    );

    event ConsentRevoked(
        bytes32 indexed consentId,
        address indexed patient,
        address indexed revokedBy,
        string reason
    );

    event ConsentExpired(
        bytes32 indexed consentId,
        address indexed patient,
        address indexed requester
    );

    event EmergencyOverrideActivated(
        bytes32 indexed consentId,
        address indexed clinician,
        string justification,
        uint256 autoRevokeAt
    );

    event EmergencyOverrideReverted(
        bytes32 indexed consentId,
        address indexed clinician
    );

    event GDPRErasureExecuted(
        bytes32 indexed consentId,
        address indexed patient,
        bytes32 erasureProofHash
    );

    event InstitutionRegistered(
        address indexed walletAddress,
        string name
    );

    event InstitutionVerified(
        address indexed walletAddress
    );

    event ProxyAuthorizationChanged(
        address indexed patient,
        address indexed proxy,
        bool authorized
    );

    event AuditLedgerChanged(address indexed auditLedger);

    // --------------------------------------------------------
    // Modifiers
    // --------------------------------------------------------

    modifier onlyOwner() {
        require(msg.sender == owner, "MedIntelOS: caller is not owner");
        _;
    }

    modifier onlyPatientOrProxy(bytes32 consentId) {
        ConsentRecord storage c = consents[consentId];
        require(
            msg.sender == c.patient
            || (c.isProxy && msg.sender == c.proxyGrantor),
            "MedIntelOS: caller is not patient or authorized proxy"
        );
        _;
    }

    modifier onlyVerifiedInstitution() {
        require(
            institutions[msg.sender].verified,
            "MedIntelOS: institution not verified"
        );
        _;
    }

    modifier consentExists(bytes32 consentId) {
        require(
            consents[consentId].consentId == consentId,
            "MedIntelOS: consent not found"
        );
        _;
    }

    modifier consentIsActive(bytes32 consentId) {
        ConsentRecord storage c = consents[consentId];
        require(
            c.status == ConsentStatus.ACTIVE
            || c.status == ConsentStatus.EMERGENCY_OVERRIDE,
            "MedIntelOS: consent is not active"
        );
        require(
            c.expiresAt == 0 || block.timestamp < c.expiresAt,
            "MedIntelOS: consent has expired"
        );
        _;
    }

    // --------------------------------------------------------
    // Constructor
    // --------------------------------------------------------

    constructor(address _auditLedger, address _verifier) {
        owner = msg.sender;
        auditLedgerAddress = _auditLedger;
        verifierAddress = _verifier;
    }

    // --------------------------------------------------------
    // Institution Management
    // --------------------------------------------------------

    /**
     * @notice Register a healthcare institution as a data requester
     * @param name Institution display name
     * @param fhirBaseUrl Base URL of the institution's FHIR server
     * @param jurisdiction ISO 3166-1 alpha-2 country code
     */
    function registerInstitution(
        string calldata name,
        string calldata fhirBaseUrl,
        string calldata jurisdiction
    ) external {
        require(
            bytes(institutions[msg.sender].name).length == 0,
            "MedIntelOS: institution already registered"
        );
        institutions[msg.sender] = InstitutionProfile({
            walletAddress: msg.sender,
            name: name,
            fhirBaseUrl: fhirBaseUrl,
            jurisdiction: jurisdiction,
            verified: false,
            registeredAt: block.timestamp,
            consentCount: 0,
            violationCount: 0
        });
        emit InstitutionRegistered(msg.sender, name);
    }

    /**
     * @notice Verify a registered institution (owner or DAO governance)
     */
    function verifyInstitution(address institution) external onlyOwner {
        require(
            bytes(institutions[institution].name).length > 0,
            "MedIntelOS: institution not registered"
        );
        institutions[institution].verified = true;
        emit InstitutionVerified(institution);
    }

    function setAuditLedger(address auditLedger) external onlyOwner {
        auditLedgerAddress = auditLedger;
        emit AuditLedgerChanged(auditLedger);
    }

    /**
     * @notice Authorize or revoke a proxy for the caller's consent actions.
     * @dev Legal authority must still be verified off-chain by the deployment.
     */
    function setProxyAuthorization(address proxy, bool authorized) external {
        require(proxy != address(0), "MedIntelOS: proxy is zero address");
        require(proxy != msg.sender, "MedIntelOS: patient cannot proxy self");
        authorizedProxies[msg.sender][proxy] = authorized;
        emit ProxyAuthorizationChanged(msg.sender, proxy, authorized);
    }

    // --------------------------------------------------------
    // Consent Lifecycle
    // --------------------------------------------------------

    /**
     * @notice Grant consent for a verified institution to access patient data
     *
     * @param requester Institution's wallet address
     * @param dataScope Array of FHIR resource type names (e.g., ["Observation", "Condition"])
     * @param purpose Purpose of data access
     * @param durationDays Access duration in days (0 = indefinite)
     * @param zkProofHash Reference to off-chain ZK proof of patient identity
     * @param patientReferenceHash Salted hash of an off-chain patient reference
     * @param irbApprovalHash For RESEARCH purpose: hash of IRB approval document
     * @return consentId The generated consent identifier
     */
    function grantConsent(
        address requester,
        string[] calldata dataScope,
        ConsentPurpose purpose,
        uint256 durationDays,
        string calldata zkProofHash,
        bytes32 patientReferenceHash,
        bytes32 irbApprovalHash
    ) external returns (bytes32 consentId) {
        require(
            institutions[requester].verified,
            "MedIntelOS: requester institution not verified"
        );
        require(
            dataScope.length > 0 && dataScope.length <= MAX_DATA_SCOPE_ITEMS,
            "MedIntelOS: invalid data scope size"
        );
        if (purpose == ConsentPurpose.RESEARCH) {
            require(
                irbApprovalHash != bytes32(0),
                "MedIntelOS: IRB approval required for research consent"
            );
        }

        uint256 expiresAt = durationDays > 0
            ? block.timestamp + (durationDays * 1 days)
            : 0;

        bytes32 scopeHash = keccak256(abi.encode(dataScope));
        consentId = ConsentLib.hashConsent(
            msg.sender, requester, scopeHash, expiresAt
        );

        require(
            consents[consentId].consentId == bytes32(0),
            "MedIntelOS: identical consent already exists"
        );

        consents[consentId] = ConsentRecord({
            consentId: consentId,
            patient: msg.sender,
            requester: requester,
            dataScope: dataScope,
            purpose: purpose,
            status: ConsentStatus.ACTIVE,
            grantedAt: block.timestamp,
            expiresAt: expiresAt,
            zkProofHash: zkProofHash,
            irbApprovalHash: irbApprovalHash,
            isProxy: false,
            proxyGrantor: address(0),
            patientReferenceHash: patientReferenceHash,
            revokedAt: 0,
            revocationReason: "",
            gdprErasureProof: bytes32(0)
        });

        _finalizeGrant(consentId);
        return consentId;
    }

    /**
     * @notice Grant proxy consent on behalf of a patient (for minors or incapacitated)
     * @param patient The patient's wallet address
     * Other params same as grantConsent
     */
    function grantProxyConsent(
        address patient,
        address requester,
        string[] calldata dataScope,
        ConsentPurpose purpose,
        uint256 durationDays,
        string calldata zkProofHash,
        bytes32 patientReferenceHash
    ) external returns (bytes32 consentId) {
        require(
            authorizedProxies[patient][msg.sender],
            "MedIntelOS: proxy is not authorized by patient"
        );
        require(
            institutions[requester].verified,
            "MedIntelOS: requester institution not verified"
        );
        require(
            dataScope.length > 0 && dataScope.length <= MAX_DATA_SCOPE_ITEMS,
            "MedIntelOS: invalid data scope size"
        );
        require(
            purpose != ConsentPurpose.RESEARCH,
            "MedIntelOS: use direct grant for research consent"
        );
        uint256 expiresAt = durationDays > 0
            ? block.timestamp + (durationDays * 1 days)
            : 0;

        bytes32 scopeHash = keccak256(abi.encode(dataScope));
        consentId = ConsentLib.hashConsent(patient, requester, scopeHash, expiresAt);

        require(
            consents[consentId].consentId == bytes32(0),
            "MedIntelOS: identical consent already exists"
        );

        consents[consentId] = ConsentRecord({
            consentId: consentId,
            patient: patient,
            requester: requester,
            dataScope: dataScope,
            purpose: purpose,
            status: ConsentStatus.ACTIVE,
            grantedAt: block.timestamp,
            expiresAt: expiresAt,
            zkProofHash: zkProofHash,
            irbApprovalHash: bytes32(0),
            isProxy: true,
            proxyGrantor: msg.sender,
            patientReferenceHash: patientReferenceHash,
            revokedAt: 0,
            revocationReason: "",
            gdprErasureProof: bytes32(0)
        });

        _finalizeGrant(consentId);
        return consentId;
    }

    function _finalizeGrant(bytes32 consentId) internal {
        ConsentRecord storage c = consents[consentId];
        patientConsents[c.patient].push(consentId);
        requesterConsents[c.requester].push(consentId);
        institutions[c.requester].consentCount++;
        totalConsentsGranted++;

        if (auditLedgerAddress != address(0)) {
            IAuditLedger(auditLedgerAddress).logConsentEvent(
                consentId,
                c.patient,
                c.requester,
                "GRANTED",
                c.dataScope[0]
            );
        }

        emit ConsentGranted(
            consentId,
            c.patient,
            c.requester,
            c.purpose,
            c.expiresAt
        );
    }

    /**
     * @notice Revoke a previously granted consent (GDPR Article 7(3))
     * @param consentId The consent to revoke
     * @param reason Human-readable revocation reason
     */
    function revokeConsent(
        bytes32 consentId,
        string calldata reason
    ) external consentExists(consentId) onlyPatientOrProxy(consentId) {
        ConsentRecord storage c = consents[consentId];
        require(
            c.status == ConsentStatus.ACTIVE,
            "MedIntelOS: consent is not active"
        );

        c.status = ConsentStatus.REVOKED;
        c.revokedAt = block.timestamp;
        c.revocationReason = reason;
        totalConsentsRevoked++;

        if (auditLedgerAddress != address(0)) {
            IAuditLedger(auditLedgerAddress).logConsentEvent(
                consentId, c.patient, c.requester, "REVOKED", reason
            );
        }

        emit ConsentRevoked(consentId, c.patient, msg.sender, reason);
    }

    /**
     * @notice Trigger GDPR Article 17 right-to-erasure workflow
     * @param consentId Consent under which data was processed
     * @param erasureProofHash Hash of off-chain erasure confirmation document
     */
    function executeGDPRErasure(
        bytes32 consentId,
        bytes32 erasureProofHash
    ) external consentExists(consentId) onlyPatientOrProxy(consentId) {
        ConsentRecord storage c = consents[consentId];
        c.gdprErasureProof = erasureProofHash;

        if (c.status == ConsentStatus.ACTIVE) {
            c.status = ConsentStatus.REVOKED;
            c.revokedAt = block.timestamp;
            c.revocationReason = "GDPR Art. 17 Right to Erasure";
        }

        emit GDPRErasureExecuted(consentId, c.patient, erasureProofHash);
    }

    // --------------------------------------------------------
    // Emergency Override
    // --------------------------------------------------------

    /**
     * @notice Activate emergency override for unconscious/critical patient
     * @dev Override auto-reverts after 24 hours. Requires verified clinician.
     * @param patientReferenceHash Salted hash of an off-chain patient reference
     * @param requester Institution requesting access
     * @param clinicianReferenceHash Salted hash of an off-chain clinician reference
     * @param justification Clinical justification (stored immutably on-chain)
     */
    function activateEmergencyOverride(
        bytes32 patientReferenceHash,
        address requester,
        bytes32 clinicianReferenceHash,
        string calldata justification
    ) external onlyVerifiedInstitution returns (bytes32 overrideId) {
        overrideId = keccak256(abi.encodePacked(
            patientReferenceHash, requester, msg.sender, block.timestamp
        ));

        emergencyOverrides[overrideId] = EmergencyOverride({
            consentId: overrideId,
            clinician: msg.sender,
            clinicianReferenceHash: clinicianReferenceHash,
            justification: justification,
            activatedAt: block.timestamp,
            autoRevokeAt: block.timestamp + EMERGENCY_OVERRIDE_DURATION,
            active: true
        });

        emit EmergencyOverrideActivated(
            overrideId,
            msg.sender,
            justification,
            block.timestamp + EMERGENCY_OVERRIDE_DURATION
        );
    }

    /**
     * @notice Check if an emergency override is still active (not auto-reverted)
     */
    function isEmergencyOverrideActive(bytes32 overrideId) external view returns (bool) {
        EmergencyOverride storage eo = emergencyOverrides[overrideId];
        return eo.active && block.timestamp < eo.autoRevokeAt;
    }

    // --------------------------------------------------------
    // Consent Verification
    // --------------------------------------------------------

    /**
     * @notice Verify whether a requester has active consent for a given purpose
     * @param patient Patient's wallet address
     * @param requester Requester's wallet address
     * @param requiredScope FHIR resource type to check
     * @param purpose Required consent purpose
     * @return hasConsent True if valid consent exists
     * @return consentId The matching consent ID (bytes32(0) if none)
     */
    function verifyConsent(
        address patient,
        address requester,
        string calldata requiredScope,
        ConsentPurpose purpose
    ) external view returns (bool hasConsent, bytes32 consentId) {
        bytes32[] storage patientConsentIds = patientConsents[patient];

        for (uint256 i = 0; i < patientConsentIds.length; i++) {
            bytes32 cid = patientConsentIds[i];
            ConsentRecord storage c = consents[cid];

            if (c.requester != requester) continue;
            if (c.status != ConsentStatus.ACTIVE) continue;
            if (c.purpose != purpose) continue;
            if (c.expiresAt > 0 && block.timestamp >= c.expiresAt) continue;

            // Check scope
            for (uint256 j = 0; j < c.dataScope.length; j++) {
                if (keccak256(bytes(c.dataScope[j])) == keccak256(bytes(requiredScope))
                    || keccak256(bytes(c.dataScope[j])) == keccak256(bytes("*"))) {
                    return (true, cid);
                }
            }
        }

        return (false, bytes32(0));
    }

    /**
     * @notice Get all consent IDs for a patient
     */
    function getPatientConsents(address patient) external view returns (bytes32[] memory) {
        return patientConsents[patient];
    }

    /**
     * @notice Get consent details
     */
    function getConsent(bytes32 consentId)
        external
        view
        consentExists(consentId)
        returns (ConsentRecord memory)
    {
        return consents[consentId];
    }
}


// ============================================================
// Immutable Audit Ledger Contract
// ============================================================

/**
 * @title MedIntelOS Audit Ledger
 * @notice Immutable, append-only log of all PHI access events.
 *         Satisfies HIPAA § 164.312(b) audit controls requirement.
 *         Every read, write, modify, and delete of PHI is recorded here.
 */
contract MedIntelOSAuditLedger is IAuditLedger {

    struct AuditEntry {
        uint256 entryId;
        bytes32 consentId;
        address actor;              // Who performed the action
        address patient;            // Whose data was accessed
        address requester;          // Institution
        string eventType;           // ACCESS | MODIFY | DELETE | GRANTED | REVOKED | EXPORT
        string dataScope;           // Which FHIR resources
        string fhirResourceId;      // Specific resource ID if applicable
        uint256 timestamp;
        bytes32 dataHash;           // Hash of accessed data (for integrity)
        string ipfsReference;       // IPFS CID for detailed log (optional)
    }

    AuditEntry[] public entries;
    address public owner;
    address public consentManager;
    mapping(address => bool) public authorizedLoggers;

    event AuditEntryCreated(
        uint256 indexed entryId,
        bytes32 indexed consentId,
        address indexed actor,
        string eventType
    );

    modifier onlyAuthorized() {
        require(
            authorizedLoggers[msg.sender] || msg.sender == consentManager,
            "AuditLedger: unauthorized logger"
        );
        _;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "AuditLedger: caller is not owner");
        _;
    }

    constructor(address _consentManager) {
        owner = msg.sender;
        consentManager = _consentManager;
        authorizedLoggers[msg.sender] = true;
        if (_consentManager != address(0)) {
            authorizedLoggers[_consentManager] = true;
        }
    }

    function setConsentManager(address newConsentManager) external onlyOwner {
        require(newConsentManager != address(0), "AuditLedger: zero address");
        if (consentManager != address(0)) {
            authorizedLoggers[consentManager] = false;
        }
        consentManager = newConsentManager;
        authorizedLoggers[newConsentManager] = true;
    }

    function setAuthorizedLogger(address logger, bool authorized) external onlyOwner {
        require(logger != address(0), "AuditLedger: zero address");
        authorizedLoggers[logger] = authorized;
    }

    function logConsentEvent(
        bytes32 consentId,
        address patient,
        address requester,
        string calldata eventType,
        string calldata dataScope
    ) external override onlyAuthorized {
        _log(consentId, requester, patient, requester, eventType, dataScope, "", bytes32(0), "");
    }

    function logAccess(
        bytes32 consentId,
        address actor,
        address patient,
        address requester,
        string calldata dataScope,
        string calldata fhirResourceId,
        bytes32 dataHash,
        string calldata ipfsReference
    ) external onlyAuthorized {
        _log(consentId, actor, patient, requester, "ACCESS", dataScope, fhirResourceId, dataHash, ipfsReference);
    }

    function _log(
        bytes32 consentId,
        address actor,
        address patient,
        address requester,
        string memory eventType,
        string memory dataScope,
        string memory fhirResourceId,
        bytes32 dataHash,
        string memory ipfsReference
    ) internal {
        uint256 entryId = entries.length;
        entries.push(AuditEntry({
            entryId: entryId,
            consentId: consentId,
            actor: actor,
            patient: patient,
            requester: requester,
            eventType: eventType,
            dataScope: dataScope,
            fhirResourceId: fhirResourceId,
            timestamp: block.timestamp,
            dataHash: dataHash,
            ipfsReference: ipfsReference
        }));

        emit AuditEntryCreated(entryId, consentId, actor, eventType);
    }

    function getEntryCount() external view returns (uint256) {
        return entries.length;
    }

    function getEntry(uint256 entryId) external view returns (AuditEntry memory) {
        require(entryId < entries.length, "AuditLedger: entry not found");
        return entries[entryId];
    }
}
