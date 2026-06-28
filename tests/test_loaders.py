import pytest

from trimgate.corpus import CorpusError, load_corpus
from trimgate.matrix import MatrixError, load_matrix
from trimgate.probe import ProbeClass, load_probeset


def test_load_matrix_rejects_scalar_where_list_expected(tmp_path):
    path = tmp_path / "m.yaml"
    # `groups: finance` (scalar) instead of `[finance]` would shred into characters.
    path.write_text(
        "identities:\n  alice: {groups: finance}\nlabel_grants:\n  finance: [x]\n",
        encoding="utf-8",
    )
    with pytest.raises(MatrixError):
        load_matrix(str(path))


def test_load_matrix_rejects_dangling_group_reference(tmp_path):
    path = tmp_path / "m.yaml"
    path.write_text(
        "identities:\n  alice: {groups: [ghost]}\nlabel_grants:\n  finance: [x]\n",
        encoding="utf-8",
    )
    with pytest.raises(MatrixError):
        load_matrix(str(path))


def test_load_corpus_rejects_row_missing_label(tmp_path):
    path = tmp_path / "c.jsonl"
    path.write_text('{"chunk_id": "c1"}\n', encoding="utf-8")
    with pytest.raises(CorpusError):
        load_corpus(str(path))


def test_load_corpus_rejects_non_string_label(tmp_path):
    path = tmp_path / "c.jsonl"
    path.write_text('{"chunk_id": "c1", "label": null}\n', encoding="utf-8")
    with pytest.raises(CorpusError):
        load_corpus(str(path))


def test_load_corpus_rejects_duplicate_json_keys(tmp_path):
    path = tmp_path / "c.jsonl"
    # last-key-wins would silently relabel a secret chunk as public.
    path.write_text(
        '{"chunk_id": "c1", "label": "fin-secret", "label": "hr-public"}\n', encoding="utf-8"
    )
    with pytest.raises(CorpusError):
        load_corpus(str(path))


def test_load_matrix_from_yaml(tmp_path):
    path = tmp_path / "matrix.yaml"
    path.write_text(
        "identities:\n"
        "  alice: { groups: [finance] }\n"
        "  carol: { groups: [finance, exec] }\n"
        "label_grants:\n"
        "  finance: [fin-public, fin-restricted]\n"
        "  exec: [exec-only]\n",
        encoding="utf-8",
    )

    matrix = load_matrix(str(path))

    assert matrix.allowed_labels("alice") == frozenset({"fin-public", "fin-restricted"})
    assert matrix.allowed_labels("carol") == frozenset(
        {"fin-public", "fin-restricted", "exec-only"}
    )


def test_load_corpus_from_jsonl(tmp_path):
    path = tmp_path / "corpus.jsonl"
    path.write_text(
        '{"chunk_id": "c1", "label": "fin-public", "text": "ignored"}\n'
        '{"chunk_id": "c2", "label": "exec-only"}\n',
        encoding="utf-8",
    )

    corpus = load_corpus(str(path))

    assert corpus.chunk_ids() == frozenset({"c1", "c2"})


def test_load_probeset_from_yaml(tmp_path):
    path = tmp_path / "probes.yaml"
    path.write_text(
        "name: seed\n"
        "probes:\n"
        "  - id: P-001\n"
        "    identity: alice\n"
        "    probe_class: retrieval\n"
        "    query: financials\n"
        "  - id: P-002\n"
        "    identity: bob\n"
        "    probe_class: direct_fetch\n"
        "    resource_ref: doc-x\n",
        encoding="utf-8",
    )

    probeset = load_probeset(str(path))

    assert probeset.name == "seed"
    assert [p.id for p in probeset.probes] == ["P-001", "P-002"]
    assert probeset.probes[0].probe_class is ProbeClass.RETRIEVAL
    assert probeset.probes[0].query == "financials"
    assert probeset.probes[1].probe_class is ProbeClass.DIRECT_FETCH
    assert probeset.probes[1].resource_ref == "doc-x"
