"""Labeled corpus: chunks under test, each carrying the label that decides who
may see it. Authorization is resolved against the access-matrix (section 0):
authorized(identity) = chunk-IDs whose label is in the identity's allowed labels.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trimgate.matrix import AccessMatrix


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    label: str


@dataclass(frozen=True)
class Corpus:
    chunks: tuple[Chunk, ...]

    def authorized_for(self, matrix: AccessMatrix, identity: str) -> frozenset[str]:
        allowed = matrix.allowed_labels(identity)
        return frozenset(c.chunk_id for c in self.chunks if c.label in allowed)

    def chunk_ids(self) -> frozenset[str]:
        return frozenset(c.chunk_id for c in self.chunks)


def load_corpus(path: str) -> Corpus:
    chunks: list[Chunk] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            chunks.append(Chunk(chunk_id=obj["chunk_id"], label=obj["label"]))
    return Corpus(chunks=tuple(chunks))
