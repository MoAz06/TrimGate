from trimgate.probe import Probe, ProbeClass, ProbeSet


def _seed() -> ProbeSet:
    return ProbeSet(
        name="seed",
        probes=(
            Probe(
                id="P-001", identity="alice", probe_class=ProbeClass.RETRIEVAL, query="financials"
            ),
            Probe(
                id="P-002",
                identity="bob",
                probe_class=ProbeClass.DIRECT_FETCH,
                resource_ref="doc-x",
            ),
        ),
    )


def test_probeset_hash_is_stable_for_identical_probes():
    assert _seed().stable_hash() == _seed().stable_hash()


def test_probeset_hash_changes_when_a_probe_field_changes():
    a = ProbeSet("seed", (Probe("P-001", "alice", ProbeClass.RETRIEVAL, query="financials"),))
    b = ProbeSet("seed", (Probe("P-001", "alice", ProbeClass.RETRIEVAL, query="salaries"),))
    assert a.stable_hash() != b.stable_hash()


def test_probeset_hash_changes_when_probe_order_changes():
    p1 = Probe("P-001", "alice", ProbeClass.RETRIEVAL, query="a")
    p2 = Probe("P-002", "bob", ProbeClass.RETRIEVAL, query="b")
    assert ProbeSet("seed", (p1, p2)).stable_hash() != ProbeSet("seed", (p2, p1)).stable_hash()
