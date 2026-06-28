"""Probe and ProbeSet: the access-control test cases (section 0).

A Probe specifies an *operation* (which adapter method, as which identity); it
carries NO expected result. Truth comes from the access-matrix, which is what
makes the corpus non-gameable. A ProbeSet is an ordered, named collection with a
deterministic stable hash so two runs of the same set are comparably identified.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum

import yaml


class ProbeClass(str, Enum):
    RETRIEVAL = "retrieval"
    DIRECT_FETCH = "direct_fetch"
    ENUMERATION = "enumeration"


@dataclass(frozen=True)
class Probe:
    id: str
    identity: str
    probe_class: ProbeClass
    query: str | None = None
    resource_ref: str | None = None

    def _canonical(self) -> dict[str, str | None]:
        return {
            "id": self.id,
            "identity": self.identity,
            "probe_class": self.probe_class.value,
            "query": self.query,
            "resource_ref": self.resource_ref,
        }


@dataclass(frozen=True)
class ProbeSet:
    name: str
    probes: tuple[Probe, ...]

    def stable_hash(self) -> str:
        payload = {"name": self.name, "probes": [p._canonical() for p in self.probes]}
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_probeset(path: str) -> ProbeSet:
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    name = data.get("name", "probeset")
    probes = tuple(
        Probe(
            id=entry["id"],
            identity=entry["identity"],
            probe_class=ProbeClass(entry["probe_class"]),
            query=entry.get("query"),
            resource_ref=entry.get("resource_ref"),
        )
        for entry in (data.get("probes") or [])
    )
    return ProbeSet(name=name, probes=probes)
