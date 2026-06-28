"""Access-diff: the trim gap.

The trim gap is the headline artifact: per identity, the set of chunk-IDs the
pipeline made improperly reachable (surfaced but not authorized), aggregated
across every probe in a run. An empty gap for every identity is a clean audit.
"""

from __future__ import annotations

from trimgate.engine import Outcome
from trimgate.runner import RunResult


def trim_gap(result: RunResult) -> dict[str, frozenset[str]]:
    gap: dict[str, set[str]] = {}
    for verdict in result.verdicts:
        if verdict.status is Outcome.LEAK:
            gap.setdefault(verdict.identity, set()).update(verdict.leaked_ids)
    return {identity: frozenset(ids) for identity, ids in gap.items()}
