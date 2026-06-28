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
            ("alice", "policy"): ["c-fin"],          # clean
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


def test_clean_run_passes():
    matrix, corpus = _setup()
    adapter = FakeAdapter(retrievals={("alice", "policy"): ["c-fin"]})
    probeset = ProbeSet("seed", (Probe("P-ok", "alice", ProbeClass.RETRIEVAL, query="policy"),))

    result = run(probeset, adapter, matrix, corpus)

    assert result.passed is True
    assert result.total_leaks == 0
    assert result.per_identity_leaks == {}
