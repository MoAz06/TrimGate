"""Labeled corpus: chunks under test, each carrying the label that decides who
may see it. Authorization is resolved against the access-matrix (section 0):
authorized(identity) = chunk-IDs whose label is in the identity's allowed labels.

The corpus is validated at construction: a chunk-ID must map to exactly one label.
A duplicated chunk-ID is rejected, because authorization unions over chunks, so a
public copy of a secret chunk-ID would otherwise silently authorize the secret.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trimgate.matrix import AccessMatrix


class CorpusError(ValueError):
    """The corpus is malformed or internally inconsistent (fail-closed)."""


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    label: str


@dataclass(frozen=True)
class Corpus:
    chunks: tuple[Chunk, ...]

    def __post_init__(self) -> None:
        seen: dict[str, str] = {}
        for chunk in self.chunks:
            if chunk.chunk_id in seen:
                raise CorpusError(
                    f"duplicate chunk_id {chunk.chunk_id!r} "
                    f"(labels {seen[chunk.chunk_id]!r} and {chunk.label!r})"
                )
            seen[chunk.chunk_id] = chunk.label

    def authorized_for(self, matrix: AccessMatrix, identity: str) -> frozenset[str]:
        allowed = matrix.allowed_labels(identity)
        return frozenset(c.chunk_id for c in self.chunks if c.label in allowed)

    def chunk_ids(self) -> frozenset[str]:
        return frozenset(c.chunk_id for c in self.chunks)


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    seen: dict[str, object] = {}
    for key, value in pairs:
        if key in seen:
            raise CorpusError(f"duplicate JSON key {key!r} (last-key-wins could relabel a chunk)")
        seen[key] = value
    return seen


def load_corpus(path: str) -> Corpus:
    chunks: list[Chunk] = []
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line, object_pairs_hook=_reject_duplicate_keys)
            except json.JSONDecodeError as exc:
                raise CorpusError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
            chunk_id, label = obj.get("chunk_id"), obj.get("label")
            if not isinstance(chunk_id, str) or not isinstance(label, str):
                raise CorpusError(f"{path}:{lineno}: chunk needs string 'chunk_id' and 'label'")
            chunks.append(Chunk(chunk_id=chunk_id, label=label))
    return Corpus(chunks=tuple(chunks))
