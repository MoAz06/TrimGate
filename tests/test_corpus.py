from trimgate.corpus import Chunk, Corpus
from trimgate.matrix import AccessMatrix


def test_authorized_for_returns_chunks_whose_label_is_granted():
    matrix = AccessMatrix(
        identities={"alice": ["finance"]},
        label_grants={"finance": ["fin-public"]},
    )
    corpus = Corpus(
        chunks=(
            Chunk("c1", "fin-public"),
            Chunk("c2", "fin-restricted"),
            Chunk("c3", "fin-public"),
        )
    )
    assert corpus.authorized_for(matrix, "alice") == frozenset({"c1", "c3"})
