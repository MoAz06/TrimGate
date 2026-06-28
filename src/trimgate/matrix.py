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


class MatrixError(ValueError):
    """The access-matrix is malformed (fail-closed at load, never silent)."""


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


def _string_list(value: object, where: str) -> list[str]:
    # A YAML scalar (e.g. `groups: finance`) must NOT be accepted: list("finance")
    # would shred it into characters and silently corrupt the policy.
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise MatrixError(f"{where} must be a list of strings, got {value!r}")
    return list(value)


def load_matrix(path: str) -> AccessMatrix:
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    label_grants = {
        group: _string_list(labels, f"label_grants[{group!r}]")
        for group, labels in (data.get("label_grants") or {}).items()
    }
    identities: dict[str, list[str]] = {}
    for identity, spec in (data.get("identities") or {}).items():
        groups = _string_list((spec or {}).get("groups", []), f"identities[{identity!r}].groups")
        dangling = [g for g in groups if g not in label_grants]
        if dangling:
            raise MatrixError(
                f"identity {identity!r} references undefined group(s) {dangling} "
                f"(not in label_grants)"
            )
        identities[identity] = groups

    return AccessMatrix(identities=identities, label_grants=label_grants)
