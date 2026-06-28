from trimgate.signing import (
    generate_private_key,
    load_private_key,
    load_public_key,
    private_key_to_pem,
    public_key_to_pem,
    sign,
    verify,
)


def test_sign_verify_round_trip():
    key = generate_private_key()
    signature = sign(b'{"verdict":"pass"}', key)
    assert verify(b'{"verdict":"pass"}', signature, key.public_key()) is True


def test_tampered_payload_fails_verification():
    key = generate_private_key()
    signature = sign(b"original bytes", key)
    assert verify(b"tampered bytes", signature, key.public_key()) is False


def test_wrong_key_fails_verification():
    signature = sign(b"payload", generate_private_key())
    assert verify(b"payload", signature, generate_private_key().public_key()) is False


def test_signature_with_injected_junk_is_rejected():
    key = generate_private_key()
    signature = sign(b"payload", key)
    tampered = signature[:5] + "@#$" + signature[5:]  # non-base64 junk
    assert verify(b"payload", tampered, key.public_key()) is False


def test_key_pem_round_trip():
    key = generate_private_key()
    private_pem = private_key_to_pem(key)
    public_pem = public_key_to_pem(key.public_key())

    reloaded_private = load_private_key(private_pem)
    reloaded_public = load_public_key(public_pem)

    signature = sign(b"x", reloaded_private)
    assert verify(b"x", signature, reloaded_public) is True
