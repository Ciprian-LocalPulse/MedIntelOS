import assert from "node:assert/strict";

import { network } from "hardhat";
import { keccak256, toBytes, zeroAddress, zeroHash } from "viem";

const patientReferenceHash = keccak256(toBytes("synthetic-patient-1"));

async function deployFixture() {
  const { viem } = await network.connect();
  const publicClient = await viem.getPublicClient();
  const [owner, patient, institution, proxy] = await viem.getWalletClients();
  const ledger = await viem.deployContract("MedIntelOSAuditLedger", [zeroAddress]);
  const manager = await viem.deployContract("MedIntelOSConsentManager", [
    ledger.address,
    zeroAddress,
  ]);

  const wait = async (hash: `0x${string}`) => {
    await publicClient.waitForTransactionReceipt({ hash });
  };

  await wait(await ledger.write.setConsentManager([manager.address]));
  await wait(
    await manager.write.registerInstitution(
      ["Example Hospital", "https://hospital.example/fhir/R5", "US"],
      { account: institution.account },
    ),
  );
  await wait(await manager.write.verifyInstitution([institution.account.address]));

  return { owner, patient, institution, proxy, manager, wait };
}

async function testPatientGrantAndRevoke() {
    const { patient, institution, manager, wait } = await deployFixture();
    await wait(
      await manager.write.grantConsent(
        [
          institution.account.address,
          ["Observation"],
          0,
          30n,
          "proof-reference",
          patientReferenceHash,
          zeroHash,
        ],
        { account: patient.account },
      ),
    );

    const consentIds = await manager.read.getPatientConsents([patient.account.address]);
    assert.equal(consentIds.length, 1);
    const consent = await manager.read.getConsent([consentIds[0]]);
    assert.equal(consent.patient, patient.account.address);

    await wait(
      await manager.write.revokeConsent([consentIds[0], "Patient request"], {
        account: patient.account,
      }),
    );
    const revoked = await manager.read.getConsent([consentIds[0]]);
    assert.equal(revoked.status, 1);
}

async function testProxyAuthorization() {
    const { patient, institution, proxy, manager, wait } = await deployFixture();
    const proxyArgs = [
      patient.account.address,
      institution.account.address,
      ["Observation"],
      0,
      7n,
      "proof-reference",
      patientReferenceHash,
    ] as const;

    await assert.rejects(
      manager.write.grantProxyConsent(proxyArgs, { account: proxy.account }),
      /proxy is not authorized by patient/,
    );

    await wait(
      await manager.write.setProxyAuthorization([proxy.account.address, true], {
        account: patient.account,
      }),
    );
    await wait(
      await manager.write.grantProxyConsent(proxyArgs, { account: proxy.account }),
    );

    const consentIds = await manager.read.getPatientConsents([patient.account.address]);
    assert.equal(consentIds.length, 1);
}

await testPatientGrantAndRevoke();
await testProxyAuthorization();
console.log("Contract integration tests passed.");
