import assert from "node:assert/strict";

import { network } from "hardhat";
import { encodeFunctionData, zeroAddress } from "viem";

async function deployFixture(threshold = 2, timelockDelay = 3600) {
  const { viem } = await network.connect();
  const publicClient = await viem.getPublicClient();
  const [signerA, signerB, signerC, outsider] = await viem.getWalletClients();

  const governance = await viem.deployContract("MedIntelOSGovernance", [
    [signerA.account.address, signerB.account.address, signerC.account.address],
    BigInt(threshold),
    BigInt(timelockDelay),
  ]);

  const ledger = await viem.deployContract("MedIntelOSAuditLedger", [zeroAddress]);
  const manager = await viem.deployContract("MedIntelOSConsentManager", [
    ledger.address,
    zeroAddress,
  ]);

  const wait = async (hash: `0x${string}`) => {
    await publicClient.waitForTransactionReceipt({ hash });
  };

  return { publicClient, signerA, signerB, signerC, outsider, governance, ledger, manager, wait };
}

async function testThresholdAndTimelockGateExecution() {
  const { signerA, signerB, governance, manager, wait } = await deployFixture(2, 3600);

  // Build a call the governance contract would relay to the consent manager
  // once it is transferred `owner` (see docs/DEPLOYMENT.md). This test
  // exercises the propose/approve/timelock gate itself, independent of that
  // transfer.
  const institution = "0x000000000000000000000000000000000000000a";
  const data = encodeFunctionData({
    abi: manager.abi,
    functionName: "verifyInstitution",
    args: [institution],
  });

  const txId = await governance.write.propose([manager.address, 0n, data], {
    account: signerA.account,
  });
  await wait(txId);

  const proposedTxId = 0n;

  // Only one approval so far (the proposer) -> not executable yet.
  await assert.rejects(
    governance.write.execute([proposedTxId], { account: signerA.account }),
    /threshold not reached/,
  );

  await wait(await governance.write.approve([proposedTxId], { account: signerB.account }));

  // Threshold reached, but timelock has not elapsed.
  await assert.rejects(
    governance.write.execute([proposedTxId], { account: signerA.account }),
    /timelock not elapsed/,
  );
}

async function testEndToEndOwnershipTransferAndExecution() {
  // timelockDelay = 0 so the happy path doesn't require chain time travel.
  const { signerA, signerB, governance, manager, wait } = await deployFixture(2, 0);

  await wait(await manager.write.transferOwnership([governance.address]));
  assert.equal((await manager.read.owner()).toLowerCase(), governance.address.toLowerCase());

  const institution = "0x0000000000000000000000000000000000000abc";
  const data = encodeFunctionData({
    abi: manager.abi,
    functionName: "verifyInstitution",
    args: [institution],
  });

  await wait(
    await governance.write.propose([manager.address, 0n, data], { account: signerA.account }),
  );
  await wait(await governance.write.approve([0n], { account: signerB.account }));

  // Threshold (2) reached and timelockDelay is 0, so this should now succeed.
  await wait(await governance.write.execute([0n], { account: signerA.account }));

  const executed = await governance.read.getTransaction([0n]);
  assert.equal(executed.executed, true);

  // A direct call from a governance signer must still fail: verifyInstitution
  // was only ever routed through governance, not made callable by signers.
  await assert.rejects(
    manager.write.verifyInstitution(["0x00000000000000000000000000000000000def"], {
      account: signerA.account,
    }),
    /caller is not owner/,
  );
}

async function testNonSignerCannotProposeOrApprove() {
  const { outsider, governance } = await deployFixture(2, 60);

  await assert.rejects(
    governance.write.propose(
      ["0x000000000000000000000000000000000000bb", 0n, "0x"],
      { account: outsider.account },
    ),
    /caller is not a signer/,
  );
}

async function testDuplicateApprovalIsIdempotent() {
  const { signerA, governance, wait } = await deployFixture(2, 60);

  const txId = await governance.write.propose(
    ["0x000000000000000000000000000000000000cc", 0n, "0x"],
    { account: signerA.account },
  );
  await wait(txId);

  const before = await governance.read.getTransaction([0n]);
  assert.equal(before.approvals, 1n);

  // Approving again from the same signer must not double count.
  await wait(await governance.write.approve([0n], { account: signerA.account }));
  const after = await governance.read.getTransaction([0n]);
  assert.equal(after.approvals, 1n);
}

async function testRevokeApprovalBeforeThreshold() {
  const { signerA, governance, wait } = await deployFixture(2, 60);

  const txId = await governance.write.propose(
    ["0x000000000000000000000000000000000000dd", 0n, "0x"],
    { account: signerA.account },
  );
  await wait(txId);

  await wait(await governance.write.revokeApproval([0n], { account: signerA.account }));
  const t = await governance.read.getTransaction([0n]);
  assert.equal(t.approvals, 0n);
}

async function testAdminFunctionsAreSelfGatedOnly() {
  const { signerA, governance } = await deployFixture(2, 60);

  // Direct calls to signer/threshold management must fail: they only work
  // via the contract calling itself through propose/approve/execute.
  await assert.rejects(
    governance.write.addSigner(["0x000000000000000000000000000000000000ee"], {
      account: signerA.account,
    }),
    /must go through propose\/approve\/execute/,
  );
  await assert.rejects(
    governance.write.setThreshold([1n], { account: signerA.account }),
    /must go through propose\/approve\/execute/,
  );
}

async function testCancelOwnProposalBeforeThreshold() {
  const { signerA, governance, wait } = await deployFixture(2, 60);

  const txId = await governance.write.propose(
    ["0x000000000000000000000000000000000000ff", 0n, "0x"],
    { account: signerA.account },
  );
  await wait(txId);

  await wait(await governance.write.cancelOwnProposal([0n], { account: signerA.account }));
  const t = await governance.read.getTransaction([0n]);
  assert.equal(t.cancelled, true);

  await assert.rejects(
    governance.write.approve([0n], { account: signerA.account }),
    /cancelled/,
  );
}

await testThresholdAndTimelockGateExecution();
await testEndToEndOwnershipTransferAndExecution();
await testNonSignerCannotProposeOrApprove();
await testDuplicateApprovalIsIdempotent();
await testRevokeApprovalBeforeThreshold();
await testAdminFunctionsAreSelfGatedOnly();
await testCancelOwnProposalBeforeThreshold();
console.log("Governance integration tests passed.");
