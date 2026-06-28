"""Golden-file tests: the canonical receipt is byte-stable.

If a code change alters the receipt bytes for the quickstart fixtures, these fail.
Regenerate deliberately (review the diff) when the schema legitimately changes.
"""

import pathlib

import pytest

from trimgate.corpus import load_corpus
from trimgate.demo import clean_adapter, leaky_adapter
from trimgate.matrix import load_matrix
from trimgate.probe import load_probeset
from trimgate.receipt import build_receipt, canonical_json
from trimgate.runner import run

QS = pathlib.Path(__file__).resolve().parents[1] / "examples" / "quickstart"
GOLDEN = pathlib.Path(__file__).resolve().parent / "golden"
MATRIX = str(QS / "access-matrix.yaml")
CORPUS = str(QS / "corpus.labeled.jsonl")
PROBES = str(QS / "probes.yaml")

_ADAPTERS = {"clean": clean_adapter, "leaky": leaky_adapter}


@pytest.mark.parametrize("name", ["clean", "leaky"])
def test_receipt_matches_golden(name):
    result = run(load_probeset(PROBES), _ADAPTERS[name](), load_matrix(MATRIX), load_corpus(CORPUS))
    produced = canonical_json(
        build_receipt(
            result, matrix_path=MATRIX, corpus_path=CORPUS, adapter=f"trimgate.demo:{name}_adapter"
        )
    )
    golden = (GOLDEN / f"receipt_{name}.json").read_text(encoding="utf-8").rstrip("\n")
    assert produced == golden
