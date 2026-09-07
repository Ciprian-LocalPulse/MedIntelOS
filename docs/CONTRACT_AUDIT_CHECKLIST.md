# Smart Contract Audit Checklist

`contracts/MedIntelOSConsent.sol` and the associated audit ledger contract
handle patient consent state and institution verification. Passing
`npm test` proves the contracts behave as the test suite describes; it does
not prove they are safe to deploy where real value, real identities, or real
consent decisions depend on them.

**Do not deploy these contracts to a public mainnet, and do not connect the
API layer to a mainnet deployment, until every item below is closed.**
Testnet deployment for integration testing is fine at any time.

## Before requesting an audit

- [ ] Freeze the contract interface (external/public function signatures) for
      the version being audited
- [ ] 100% branch coverage in `contract-tests/`, including revert paths
- [ ] Static analysis run and triaged (Slither, Mythril, or equivalent)
- [ ] Internal review of every `onlyOwner` / role-gated function against
      `docs/THREAT_MODEL.md`'s "Smart-contract privilege abuse" row
- [ ] Documented upgrade path (or explicit non-upgradeability) and its
      consequences for existing consent records

## Audit scope to request

- [ ] Access control correctness (owner, proxy authorization, institution
      verification)
- [ ] Reentrancy and external call safety
- [ ] Integer overflow/underflow in any custom arithmetic
- [ ] Front-running / transaction-ordering risk on consent state changes
- [ ] Gas griefing / denial-of-service vectors on functions with unbounded
      loops or arrays
- [ ] Consistency between `MedIntelOSAuditLedger` and `MedIntelOSConsentManager`
      state (the deployment sequence in `README.md` — ledger first, then
      manager, then `setConsentManager` — is a manual step; verify it cannot
      be left in an inconsistent state)

## Before mainnet (or any production network)

- [ ] Audit findings resolved or explicitly accepted in writing by the
      contract owner, with residual risk documented
- [ ] Multisig configured for owner-only functions (see `docs/ROADMAP.md`
      0.8.0)
- [ ] Timelock configured for any function that changes consent semantics or
      administration
- [ ] Incident response plan for a compromised owner key, covering pausing,
      migration, and user communication
- [ ] Confirmation that no PHI, names, identifiers, or clinical notes are
      written on-chain, including in event logs — re-verify this after every
      contract change, not just once

## After deployment

- [ ] Monitoring configured for owner-function calls and unexpected state
      transitions
- [ ] A published contract address and verified source on the target chain's
      block explorer
- [ ] A rotation/runbook for what happens if the audit firm later publishes a
      retroactive finding
