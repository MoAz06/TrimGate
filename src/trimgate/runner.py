"""Deterministic probe runner: executes a ProbeSet against an adapter.

Stable ordering (probe order is preserved), no randomness, no LLM. Given the same
inputs it produces the same verdicts. The run fails (for CI) if any probe is a
LEAK or a fail-closed ERROR; a SKIPPED probe does not fail the run.
"""

from __future__ import annotations

from dataclasses import dataclass

from trimgate.adapter import RagAdapter
from trimgate.corpus import Corpus
from trimgate.engine import Outcome, Verdict, evaluate
from trimgate.matrix import AccessMatrix
from trimgate.probe import ProbeSet


@dataclass(frozen=True)
class RunResult:
    probeset_hash: str
    verdicts: tuple[Verdict, ...]

    @property
    def passed(self) -> bool:
        return not any(v.status in (Outcome.LEAK, Outcome.ERROR) for v in self.verdicts)

    @property
    def total_leaks(self) -> int:
        return sum(1 for v in self.verdicts if v.status is Outcome.LEAK)

    @property
    def total_errors(self) -> int:
        return sum(1 for v in self.verdicts if v.status is Outcome.ERROR)

    @property
    def per_identity_leaks(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for v in self.verdicts:
            if v.status is Outcome.LEAK:
                counts[v.identity] = counts.get(v.identity, 0) + 1
        return counts


def run(probeset: ProbeSet, adapter: RagAdapter, matrix: AccessMatrix, corpus: Corpus) -> RunResult:
    verdicts = tuple(evaluate(p, adapter, matrix, corpus) for p in probeset.probes)
    return RunResult(probeset_hash=probeset.stable_hash(), verdicts=verdicts)
