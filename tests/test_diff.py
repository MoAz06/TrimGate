import pathlib

from trimgate.corpus import load_corpus
from trimgate.demo import clean_adapter, leaky_adapter
from trimgate.diff import trim_gap
from trimgate.matrix import load_matrix
from trimgate.probe import load_probeset
from trimgate.runner import run

QS = pathlib.Path(__file__).resolve().parents[1] / "examples" / "quickstart"


def _run(adapter):
    matrix = load_matrix(str(QS / "access-matrix.yaml"))
    corpus = load_corpus(str(QS / "corpus.labeled.jsonl"))
    probeset = load_probeset(str(QS / "probes.yaml"))
    return run(probeset, adapter, matrix, corpus)


def test_trim_gap_aggregates_improperly_reachable_chunks_per_identity():
    gap = trim_gap(_run(leaky_adapter()))
    # bob's retrieval and direct-fetch both leaked the same finance chunk
    assert gap == {"bob": frozenset({"c-salary"})}


def test_trim_gap_is_empty_on_a_clean_run():
    assert trim_gap(_run(clean_adapter())) == {}
