import pytest

from trimgate.matrix import AccessMatrix, UnknownIdentityError


def test_allowed_labels_unions_grants_of_identitys_groups():
    matrix = AccessMatrix(
        identities={"alice": ["finance"]},
        label_grants={"finance": ["fin-public", "fin-restricted"], "eng": ["eng-public"]},
    )
    assert matrix.allowed_labels("alice") == frozenset({"fin-public", "fin-restricted"})


def test_unknown_identity_raises_fail_closed():
    matrix = AccessMatrix(
        identities={"alice": ["finance"]},
        label_grants={"finance": ["fin-public"]},
    )
    with pytest.raises(UnknownIdentityError):
        matrix.allowed_labels("ghost")
