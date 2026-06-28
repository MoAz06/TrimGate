import pathlib

from trimgate.corpus import load_corpus
from trimgate.demo import clean_adapter, leaky_adapter
from trimgate.matrix import load_matrix
from trimgate.probe import load_probeset
from trimgate.receipt import build_receipt, canonical_json, to_markdown
from trimgate.runner import run

QS = pathlib.Path(__file__).resolve().parents[1] / "examples" / "quickstart"
MATRIX = str(QS / "access-matrix.yaml")
CORPUS = str(QS / "corpus.labeled.jsonl")
PROBES = str(QS / "probes.yaml")


def _run(adapter):
    return run(load_probeset(PROBES), adapter, load_matrix(MATRIX), load_corpus(CORPUS))


def _receipt(adapter):
    return build_receipt(_run(adapter), matrix_path=MATRIX, corpus_path=CORPUS)


def test_receipt_structure_for_leaky_run():
    receipt = _receipt(leaky_adapter())

    assert receipt["schema"] == "trimgate/receipt@1"
    assert receipt["verdict"] == "fail"
    assert receipt["summary"]["total_probes"] == 4
    assert receipt["summary"]["leaked_probes"] == 2
    assert receipt["summary"]["per_identity_leaks"] == {"bob": 2}
    assert len(receipt["inputs"]["matrix_sha256"]) == 64  # hex sha256
    assert len(receipt["inputs"]["corpus_sha256"]) == 64

    p2 = next(r for r in receipt["results"] if r["probe_id"] == "P-002")
    assert p2["outcome"] == "leak"
    assert p2["leaked_ids"] == ["c-salary"]
    assert p2["surfaced_ids"] == ["c-readme", "c-salary"]  # sorted


def test_clean_receipt_verdict_is_pass():
    receipt = _receipt(clean_adapter())
    assert receipt["verdict"] == "pass"
    assert receipt["summary"]["leaked_probes"] == 0
    assert receipt["summary"]["per_identity_leaks"] == {}


def test_canonical_json_is_byte_stable_and_excludes_timestamp():
    first = canonical_json(_receipt(leaky_adapter()))
    second = canonical_json(_receipt(leaky_adapter()))
    assert first == second
    assert "timestamp" not in first
    # canonical: sorted keys, no insignificant whitespace
    assert first.startswith('{"inputs":')


def test_markdown_report_names_the_leak():
    md = to_markdown(_receipt(leaky_adapter()))
    assert "FAIL" in md
    assert "c-salary" in md
    assert "bob" in md
