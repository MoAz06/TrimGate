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

from typing import Protocol, Sequence, runtime_checkable

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
