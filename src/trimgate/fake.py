"""Fake in-memory adapter: a fully synthetic doc store for tests and the demo.

It returns exactly the chunk-IDs it was seeded with per (identity, operation), so
a test can model both correct trimming (seed only authorized IDs) and a
deliberate leak (seed an unauthorized ID). Deterministic by construction.
"""

from __future__ import annotations

from trimgate.adapter import Identity


class FakeAdapter:
    def __init__(
        self,
        retrievals: dict[tuple[str, str], list[str]] | None = None,
        fetches: dict[tuple[str, str], list[str]] | None = None,
        listings: dict[str, list[str]] | None = None,
    ) -> None:
        # retrievals keyed by (identity, query); fetches by (identity, resource_ref).
        self._retrievals = dict(retrievals or {})
        self._fetches = dict(fetches or {})
        self._listings = dict(listings or {})

    def retrieve(self, query: str, identity: Identity) -> list[str]:
        return list(self._retrievals.get((identity, query), []))

    def fetch_resource(self, resource_ref: str, identity: Identity) -> list[str]:
        return list(self._fetches.get((identity, resource_ref), []))

    def list_resources(self, identity: Identity) -> list[str]:
        return list(self._listings.get(identity, []))
