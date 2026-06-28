from trimgate.corpus import Chunk, Corpus
from trimgate.engine import Outcome, evaluate
from trimgate.fake import FakeAdapter
from trimgate.matrix import AccessMatrix
from trimgate.probe import Probe, ProbeClass


class RetrieveOnly:
    """An adapter implementing only the required method (no optional methods)."""

    def retrieve(self, query, identity):
        return []


class Boom:
    """An adapter whose backend fails."""

    def retrieve(self, query, identity):
        raise RuntimeError("backend down")


def test_retrieval_probe_leak_is_detected():
    matrix = AccessMatrix(
        identities={"bob": ["eng"]},
        label_grants={"eng": ["eng-public"], "finance": ["fin-secret"]},
    )
    corpus = Corpus(chunks=(Chunk("c-eng", "eng-public"), Chunk("c-salary", "fin-secret")))
    # bob's retriever wrongly surfaces the finance chunk -> a leak
    adapter = FakeAdapter(retrievals={("bob", "salary bands"): ["c-eng", "c-salary"]})
    probe = Probe("P-1", "bob", ProbeClass.RETRIEVAL, query="salary bands")

    verdict = evaluate(probe, adapter, matrix, corpus)

    assert verdict.status is Outcome.LEAK
    assert verdict.surfaced_ids == frozenset({"c-eng", "c-salary"})
    assert verdict.leaked_ids == frozenset({"c-salary"})


def test_clean_retrieval_passes():
    matrix = AccessMatrix(identities={"alice": ["finance"]}, label_grants={"finance": ["fin-public"]})
    corpus = Corpus(chunks=(Chunk("c1", "fin-public"), Chunk("c2", "fin-public")))
    adapter = FakeAdapter(retrievals={("alice", "policy"): ["c1", "c2"]})
    probe = Probe("P-ok", "alice", ProbeClass.RETRIEVAL, query="policy")

    verdict = evaluate(probe, adapter, matrix, corpus)

    assert verdict.status is Outcome.PASS
    assert verdict.leaked_ids == frozenset()


def test_direct_fetch_probe_uses_fetch_resource_and_flags_leak():
    matrix = AccessMatrix(identities={"bob": ["eng"]}, label_grants={"eng": ["eng-public"]})
    corpus = Corpus(chunks=(Chunk("c-eng", "eng-public"), Chunk("c-secret", "exec-only")))
    adapter = FakeAdapter(fetches={("bob", "doc-secret"): ["c-secret"]})
    probe = Probe("P-2", "bob", ProbeClass.DIRECT_FETCH, resource_ref="doc-secret")

    verdict = evaluate(probe, adapter, matrix, corpus)

    assert verdict.status is Outcome.LEAK
    assert verdict.leaked_ids == frozenset({"c-secret"})


def test_enumeration_probe_uses_list_resources_and_passes_when_authorized():
    matrix = AccessMatrix(identities={"alice": ["finance"]}, label_grants={"finance": ["fin-public"]})
    corpus = Corpus(chunks=(Chunk("c1", "fin-public"),))
    adapter = FakeAdapter(listings={"alice": ["c1"]})
    probe = Probe("P-3", "alice", ProbeClass.ENUMERATION)

    verdict = evaluate(probe, adapter, matrix, corpus)

    assert verdict.status is Outcome.PASS
    assert verdict.surfaced_ids == frozenset({"c1"})


def test_probe_needing_unimplemented_optional_method_is_skipped():
    matrix = AccessMatrix(identities={"bob": ["eng"]}, label_grants={"eng": ["eng-public"]})
    corpus = Corpus(chunks=(Chunk("c-eng", "eng-public"),))
    probe = Probe("P-skip", "bob", ProbeClass.DIRECT_FETCH, resource_ref="doc-x")

    verdict = evaluate(probe, RetrieveOnly(), matrix, corpus)

    assert verdict.status is Outcome.SKIPPED


def test_adapter_error_is_fail_closed_error():
    matrix = AccessMatrix(identities={"bob": ["eng"]}, label_grants={"eng": ["eng-public"]})
    corpus = Corpus(chunks=(Chunk("c-eng", "eng-public"),))
    probe = Probe("P-boom", "bob", ProbeClass.RETRIEVAL, query="x")

    verdict = evaluate(probe, Boom(), matrix, corpus)

    assert verdict.status is Outcome.ERROR


def test_unknown_surfaced_chunk_is_fail_closed_error():
    matrix = AccessMatrix(identities={"bob": ["eng"]}, label_grants={"eng": ["eng-public"]})
    corpus = Corpus(chunks=(Chunk("c-eng", "eng-public"),))
    adapter = FakeAdapter(retrievals={("bob", "x"): ["c-ghost"]})  # id not in corpus
    probe = Probe("P-ghost", "bob", ProbeClass.RETRIEVAL, query="x")

    verdict = evaluate(probe, adapter, matrix, corpus)

    assert verdict.status is Outcome.ERROR
    assert verdict.leaked_ids == frozenset()


def test_unknown_identity_is_fail_closed_error():
    matrix = AccessMatrix(identities={"bob": ["eng"]}, label_grants={"eng": ["eng-public"]})
    corpus = Corpus(chunks=(Chunk("c-eng", "eng-public"),))
    adapter = FakeAdapter(retrievals={("ghost", "x"): []})
    probe = Probe("P-id", "ghost", ProbeClass.RETRIEVAL, query="x")

    verdict = evaluate(probe, adapter, matrix, corpus)

    assert verdict.status is Outcome.ERROR
