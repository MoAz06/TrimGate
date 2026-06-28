from trimgate.corpus import Chunk, Corpus
from trimgate.fake import FakeAdapter
from trimgate.matrix import AccessMatrix
from trimgate.probe import Probe, ProbeClass, ProbeSet
from trimgate.runner import run


def _setup():
    matrix = AccessMatrix(
        identities={"alice": ["finance"], "bob": ["eng"]},
        label_grants={"finance": ["fin-public"], "eng": ["eng-public"]},
    )
    corpus = Corpus(
        chunks=(
            Chunk("c-fin", "fin-public"),
            Chunk("c-eng", "eng-public"),
            Chunk("c-secret", "exec-only"),
        )
    )
    return matrix, corpus


def test_run_collects_verdicts_in_probe_order_and_flags_failure():
    matrix, corpus = _setup()
    adapter = FakeAdapter(
        retrievals={
            ("alice", "policy"): ["c-fin"],  # clean
            ("bob", "secrets"): ["c-eng", "c-secret"],  # leaks c-secret
        }
    )
    probeset = ProbeSet(
        name="seed",
        probes=(
            Probe("P-ok", "alice", ProbeClass.RETRIEVAL, query="policy"),
            Probe("P-leak", "bob", ProbeClass.RETRIEVAL, query="secrets"),
        ),
    )

    result = run(probeset, adapter, matrix, corpus)

    assert [v.probe_id for v in result.verdicts] == ["P-ok", "P-leak"]
    assert result.passed is False
    assert result.total_leaks == 1
    assert result.per_identity_leaks == {"bob": 1}
    assert result.probeset_hash == probeset.stable_hash()


def test_error_probe_fails_the_run():
    # An unknown identity is a fail-closed ERROR; it must fail the run, not pass.
    matrix, corpus = _setup()
    adapter = FakeAdapter()
    probeset = ProbeSet("seed", (Probe("P-err", "ghost", ProbeClass.RETRIEVAL, query="x"),))

    result = run(probeset, adapter, matrix, corpus)

    assert result.passed is False
    assert result.total_errors == 1
    assert result.total_leaks == 0


class _RetrieveOnly:
    def retrieve(self, query, identity):
        return []


def test_total_skipped_counts_skipped_probes():
    # A direct_fetch probe against an adapter without fetch_resource is SKIPPED;
    # the count must be visible so skipped coverage is not mistaken for clean.
    matrix, corpus = _setup()
    probeset = ProbeSet("s", (Probe("P", "alice", ProbeClass.DIRECT_FETCH, resource_ref="x"),))
    result = run(probeset, _RetrieveOnly(), matrix, corpus)
    assert result.total_skipped == 1


def test_all_skipped_run_does_not_pass():
    # Every probe skipped -> nothing was actually audited -> not a pass.
    matrix, corpus = _setup()
    probeset = ProbeSet(
        "s",
        (
            Probe("P1", "alice", ProbeClass.DIRECT_FETCH, resource_ref="x"),
            Probe("P2", "alice", ProbeClass.ENUMERATION),
        ),
    )
    result = run(probeset, _RetrieveOnly(), matrix, corpus)
    assert result.total_skipped == 2
    assert result.passed is False


def test_empty_probeset_does_not_pass():
    # A vacuous run (zero probes) proves nothing; it must not be reported PASS.
    matrix, corpus = _setup()
    result = run(ProbeSet("empty", ()), FakeAdapter(), matrix, corpus)
    assert result.passed is False


def test_clean_run_passes():
    matrix, corpus = _setup()
    adapter = FakeAdapter(retrievals={("alice", "policy"): ["c-fin"]})
    probeset = ProbeSet("seed", (Probe("P-ok", "alice", ProbeClass.RETRIEVAL, query="policy"),))

    result = run(probeset, adapter, matrix, corpus)

    assert result.passed is True
    assert result.total_leaks == 0
    assert result.per_identity_leaks == {}
