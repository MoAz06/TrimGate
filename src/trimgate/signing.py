"""Ed25519 signing for the receipt.

The signature is computed over the canonical (RFC 8785) JSON bytes of the
receipt, so a passing verdict cannot be silently edited after the fact. Keys are
serialized as PEM (PKCS8 private, SubjectPublicKeyInfo public); signatures are
base64. Signing and verification are fully offline: an auditor verifies a receipt
with only the public key and the canonical bytes, no network and no re-run.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


def generate_private_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


def sign(payload: bytes, private_key: Ed25519PrivateKey) -> str:
    return base64.b64encode(private_key.sign(payload)).decode("ascii")


def verify(payload: bytes, signature_b64: str, public_key: Ed25519PublicKey) -> bool:
    try:
        # validate=True rejects junk characters instead of silently stripping them,
        # so a corrupted .sig file fails rather than appearing valid.
        signature = base64.b64decode(signature_b64.strip(), validate=True)
        public_key.verify(signature, payload)
    except (InvalidSignature, ValueError):
        return False
    return True


def key_fingerprint(public_key: Ed25519PublicKey) -> str:
    """A stable fingerprint of a public key (sha256 of its SPKI PEM), for pinning."""
    return hashlib.sha256(public_key_to_pem(public_key)).hexdigest()


def private_key_to_pem(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def public_key_to_pem(public_key: Ed25519PublicKey) -> bytes:
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def load_private_key(pem: bytes) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(pem, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("not an Ed25519 private key")
    return key


def load_public_key(pem: bytes) -> Ed25519PublicKey:
    key = serialization.load_pem_public_key(pem)
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("not an Ed25519 public key")
    return key
