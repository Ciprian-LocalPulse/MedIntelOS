from medintelos.audit import AuditChain


def test_audit_chain_verifies() -> None:
    chain = AuditChain()
    first = chain.append(actor="tester", action="create", resource="Patient/p1")
    second = chain.append(actor="tester", action="read", resource="Patient/p1")

    assert second.previous_hash == first.entry_hash
    assert chain.verify() is True
