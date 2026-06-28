"""The adapter contract: the single seam between TrimGate and a host RAG system.

Per the reconciled v1 contract (section 0): one REQUIRED method `retrieve`, plus
two OPTIONAL methods `fetch_resource` and `list_resources`, all returning
chunk-IDs. The optional methods are detected at runtime (a probe that needs an
unimplemented one is skipped and logged, never silently passed), so the base
protocol declares only the required method.

The adapter is the only impure boundary. It may do I/O and be non-deterministic;
TrimGate judges exactly what it returned. A genuine backend failure should raise
AdapterError, which TrimGate records fail-closed.
"""

from __future__ import annotations

import importlib
from collections.abc import Sequence
from typing import Protocol, cast, runtime_checkable

Identity = str  # access-matrix key

# Optional adapter method names, detected via hasattr by the engine.
FETCH_RESOURCE = "fetch_resource"
LIST_RESOURCES = "list_resources"


@runtime_checkable
class RagAdapter(Protocol):
    def retrieve(self, query: str, identity: Identity) -> Sequence[str]:
        """Return the chunk-IDs the host retriever would surface for (query, identity)."""
        ...


class AdapterError(Exception):
    """Genuine backend failure (timeout, auth error). Recorded fail-closed."""


def resolve_adapter(spec: str) -> RagAdapter:
    """Resolve a MODULE:ATTR import path to an adapter instance.

    ATTR may be a class (instantiated no-args) or a factory (called); an already
    constructed instance is used as-is.
    """
    module_name, sep, attr = spec.partition(":")
    if not sep or not attr:
        raise ValueError(f"adapter must be MODULE:ATTR, got {spec!r}")
    obj = getattr(importlib.import_module(module_name), attr)
    return cast("RagAdapter", obj() if callable(obj) else obj)
