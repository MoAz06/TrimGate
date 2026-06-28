"""The assertion engine: the heart of the trust path.

For each probe it compares the chunk-IDs the adapter surfaced against the set the
identity is authorized to see (derived from the access-matrix), by pure set
arithmetic. No model, no fuzzy match, no randomness. Binary verdict: a probe is a
LEAK iff it surfaced any chunk outside the authorized set, else PASS.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, cast

from trimgate.adapter import RagAdapter
from trimgate.corpus import Corpus
from trimgate.matrix import AccessMatrix, UnknownIdentityError
from trimgate.probe import Probe, ProbeClass

# Probe class -> the optional adapter method it requires (retrieval needs the
# required `retrieve`, so it is absent here and never skips).
_REQUIRED_OPTIONAL_METHOD = {
    ProbeClass.DIRECT_FETCH: "fetch_resource",
    ProbeClass.ENUMERATION: "list_resources",
}


class Outcome(StrEnum):
    PASS = "pass"
    LEAK = "leak"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class Verdict:
    probe_id: str
    identity: str
    probe_class: ProbeClass
    status: Outcome
    surfaced_ids: frozenset[str]
    leaked_ids: frozenset[str]
    detail: str = ""


def _surface(probe: Probe, adapter: RagAdapter) -> list[str]:
    """Call the adapter method the probe's class selects, returning chunk-IDs.

    The optional methods are reached via getattr so the base protocol need only
    declare `retrieve`; presence is checked by the caller before dispatch.
    """
    if probe.probe_class is ProbeClass.RETRIEVAL:
        if probe.query is None:
            raise ValueError(f"retrieval probe {probe.id} has no query")
        return list(adapter.retrieve(probe.query, probe.identity))
    if probe.probe_class is ProbeClass.DIRECT_FETCH:
        if probe.resource_ref is None:
            raise ValueError(f"direct_fetch probe {probe.id} has no resource_ref")
        return list(cast("Any", adapter).fetch_resource(probe.resource_ref, probe.identity))
    if probe.probe_class is ProbeClass.ENUMERATION:
        return list(cast("Any", adapter).list_resources(probe.identity))
    raise ValueError(f"unknown probe_class: {probe.probe_class!r}")


def _verdict(
    probe: Probe,
    status: Outcome,
    surfaced: frozenset[str],
    leaked: frozenset[str],
    detail: str = "",
) -> Verdict:
    return Verdict(probe.id, probe.identity, probe.probe_class, status, surfaced, leaked, detail)


def evaluate(probe: Probe, adapter: RagAdapter, matrix: AccessMatrix, corpus: Corpus) -> Verdict:
    empty: frozenset[str] = frozenset()

    # A probe whose class needs an unimplemented optional method is skipped and
    # logged (never silently passed).
    needed = _REQUIRED_OPTIONAL_METHOD.get(probe.probe_class)
    if needed is not None and not hasattr(adapter, needed):
        return _verdict(
            probe,
            Outcome.SKIPPED,
            empty,
            empty,
            detail=f"adapter has no optional method {needed!r}",
        )

    # The adapter is the only impure boundary; any failure is fail-closed.
    try:
        surfaced = frozenset(_surface(probe, adapter))
    except Exception as exc:  # noqa: BLE001 - fail-closed on any backend failure
        return _verdict(probe, Outcome.ERROR, empty, empty, detail=f"adapter error: {exc}")

    # An identity not declared in the matrix is a config error, never a pass.
    try:
        authorized = corpus.authorized_for(matrix, probe.identity)
    except UnknownIdentityError:
        return _verdict(
            probe, Outcome.ERROR, surfaced, empty, detail=f"unknown identity {probe.identity!r}"
        )

    # A surfaced chunk-ID that the corpus cannot classify is fail-closed, never
    # treated as authorized.
    unknown = surfaced - corpus.chunk_ids()
    if unknown:
        return _verdict(
            probe, Outcome.ERROR, surfaced, empty, detail=f"unknown chunk(s): {sorted(unknown)}"
        )

    leaked = surfaced - authorized
    status = Outcome.LEAK if leaked else Outcome.PASS
    return _verdict(probe, status, surfaced, leaked)
