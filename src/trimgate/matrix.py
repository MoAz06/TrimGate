"""Access-matrix layer: resolves an identity to the corpus labels it may see.

Per the reconciled v1 contract (handoff section 0): authorized(identity) is
derived here, from the matrix, independent of the retriever, to avoid the
circularity of re-running the system under test's own trimming filter.
"""

from __future__ import annotations

from dataclasses import dataclass

import yaml


class UnknownIdentityError(KeyError):
    """Raised when an identity is not declared in the access-matrix.

    Fail-closed: an unknown identity is an error, never a silent empty grant.
    """


@dataclass(frozen=True)
class AccessMatrix:
    identities: dict[str, list[str]]
    label_grants: dict[str, list[str]]

    def allowed_labels(self, identity: str) -> frozenset[str]:
        if identity not in self.identities:
            raise UnknownIdentityError(identity)
        labels: set[str] = set()
        for group in self.identities[identity]:
            labels.update(self.label_grants.get(group, []))
        return frozenset(labels)


def load_matrix(path: str) -> AccessMatrix:
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    identities = {
        identity: list((spec or {}).get("groups", []))
        for identity, spec in (data.get("identities") or {}).items()
    }
    label_grants = {
        group: list(labels) for group, labels in (data.get("label_grants") or {}).items()
    }
    return AccessMatrix(identities=identities, label_grants=label_grants)
