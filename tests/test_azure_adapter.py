import pytest

from trimgate.adapter import RagAdapter
from trimgate.adapters.azure import AzureSearchAdapter, build_security_filter

# Per-group `eq` clauses ORed together -- no comma delimiter to collide with.
EXPECTED_FILTER = (
    "authorized_principals/any(g: g eq 'grp-a') or authorized_principals/any(g: g eq 'grp-b')"
)


class FakeSearchClient:
    """Stand-in for azure.search.documents.SearchClient (no network, no SDK)."""

    def __init__(self, docs):
        self._docs = docs
        self.last_call = None

    def search(self, *, search_text, top, filter, select):  # noqa: A002 - mirrors SDK kwarg
        self.last_call = {
            "search_text": search_text,
            "top": top,
            "filter": filter,
            "select": select,
        }
        return list(self._docs)


def test_build_security_filter_is_per_group_eq_or():
    assert build_security_filter("authorized_principals", ["grp-a", "grp-b"]) == EXPECTED_FILTER


def test_build_security_filter_rejects_comma_in_group_id():
    # A comma would split into extra match tokens -> authorization bypass.
    with pytest.raises(ValueError):
        build_security_filter("f", ["grp-a,grp-exec"])


def test_build_security_filter_rejects_quote_in_group_id():
    with pytest.raises(ValueError):
        build_security_filter("f", ["o'brien"])


def test_build_security_filter_rejects_empty_groups():
    with pytest.raises(ValueError):
        build_security_filter("f", [])


def test_build_security_filter_rejects_tautology_field_name():
    # An unvalidated field name like "true or x" would make the filter always true.
    with pytest.raises(ValueError):
        build_security_filter("true or x", ["g1"])


def test_build_security_filter_rejects_whitespace_padded_group_id():
    with pytest.raises(ValueError):
        build_security_filter("f", ["g1 "])


def test_retrieve_applies_trimming_filter_and_maps_chunk_ids():
    client = FakeSearchClient([{"chunk_id": "c1"}, {"chunk_id": "c2"}])
    groups = {"alice": ["grp-a", "grp-b"]}
    adapter = AzureSearchAdapter(client, group_resolver=lambda identity: groups[identity])

    surfaced = adapter.retrieve("quarterly financials", "alice")

    assert surfaced == ["c1", "c2"]
    assert client.last_call["filter"] == EXPECTED_FILTER
    assert client.last_call["select"] == ["chunk_id"]
    assert client.last_call["search_text"] == "quarterly financials"


def test_retrieve_default_top_is_audit_sized():
    # A small top-k could truncate an unauthorized chunk out of the observed
    # window (a false PASS), so the audit default must be large.
    client = FakeSearchClient([])
    AzureSearchAdapter(client, group_resolver=lambda identity: ["grp-a"]).retrieve("q", "i")
    assert client.last_call["top"] >= 1000


def test_retrieve_with_no_groups_returns_empty_without_querying():
    # An identity with zero groups can see nothing group-gated -> fail-closed.
    client = FakeSearchClient([{"chunk_id": "c1"}])
    adapter = AzureSearchAdapter(client, group_resolver=lambda identity: [])

    assert adapter.retrieve("q", "nobody") == []
    assert client.last_call is None  # never issued a query


def test_azure_adapter_satisfies_rag_adapter_protocol():
    adapter = AzureSearchAdapter(FakeSearchClient([]), group_resolver=lambda identity: [])
    assert isinstance(adapter, RagAdapter)
