"""Week 1 determinism guarantee: the runner is a pure function of its inputs.

Same matrix + corpus + probeset + adapter responses -> identical verdicts, in the
same order, every time. This is what makes the verdict trustworthy as a CI gate.
"""

from trimgate.corpus import load_corpus
from trimgate.demo import leaky_adapter
from trimgate.matrix import load_matrix
from trimgate.probe import load_probeset
from trimgate.runner import run

import pathlib

QS = pathlib.Path(__file__).resolve().parents[1] / "examples" / "quickstart"


def test_run_is_byte_stable_across_runs():
    matrix = load_matrix(str(QS / "access-matrix.yaml"))
    corpus = load_corpus(str(QS / "corpus.labeled.jsonl"))
    probeset = load_probeset(str(QS / "probes.yaml"))

    first = run(probeset, leaky_adapter(), matrix, corpus)
    second = run(probeset, leaky_adapter(), matrix, corpus)

    assert first.verdicts == second.verdicts
    assert first.probeset_hash == second.probeset_hash
    assert first.passed is False
    assert first.total_leaks == 2
