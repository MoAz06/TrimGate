from trimgate.adapter import RagAdapter
from trimgate.fake import FakeAdapter


def test_fake_adapter_retrieve_returns_seeded_chunk_ids():
    adapter = FakeAdapter(retrievals={("alice", "financials"): ["c1", "c3"]})
    assert list(adapter.retrieve("financials", "alice")) == ["c1", "c3"]


def test_fake_adapter_unseeded_retrieve_returns_empty():
    assert list(FakeAdapter().retrieve("anything", "nobody")) == []


def test_fake_adapter_satisfies_rag_adapter_protocol():
    assert isinstance(FakeAdapter(), RagAdapter)
