import pathlib

from trimgate.cli import main
from trimgate.signing import key_fingerprint, load_private_key, load_public_key

QS = pathlib.Path(__file__).resolve().parents[1] / "examples" / "quickstart"


def _run_args(
    out: pathlib.Path, key: pathlib.Path, adapter: str = "trimgate.demo:clean_adapter"
) -> list[str]:
    return [
        "run",
        "--adapter",
        adapter,
        "--matrix",
        str(QS / "access-matrix.yaml"),
        "--corpus",
        str(QS / "corpus.labeled.jsonl"),
        "--probes",
        str(QS / "probes.yaml"),
        "--out",
        str(out),
        "--sign",
        "--key",
        str(key),
    ]


def _keypair(tmp_path: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    private = tmp_path / "key.pem"
    public = tmp_path / "key.pub"
    assert main(["keygen", "--private", str(private), "--public", str(public)]) == 0
    return private, public


def test_keygen_writes_loadable_keypair(tmp_path):
    private, public = _keypair(tmp_path)
    load_private_key(private.read_bytes())  # does not raise
    load_public_key(public.read_bytes())


def test_run_sign_then_verify_roundtrip(tmp_path):
    private, public = _keypair(tmp_path)
    out = tmp_path / "receipt.json"
    sig = tmp_path / "receipt.json.sig"

    code = main(_run_args(out, private))  # clean adapter -> pass
    assert code == 0
    assert sig.exists()

    verify_code = main(["verify", str(out), "--sig", str(sig), "--public", str(public)])
    assert verify_code == 0


def test_verify_rejects_a_validly_signed_fail_receipt(tmp_path):
    # A correctly-signed receipt whose audit verdict is "fail" must NOT verify OK.
    private, public = _keypair(tmp_path)
    out = tmp_path / "receipt.json"
    sig = tmp_path / "receipt.json.sig"
    main(_run_args(out, private, adapter="trimgate.demo:leaky_adapter"))

    code = main(["verify", str(out), "--sig", str(sig), "--public", str(public)])
    assert code != 0  # signature is valid, but the audit failed


def test_verify_detects_tampering(tmp_path):
    private, public = _keypair(tmp_path)
    out = tmp_path / "receipt.json"
    sig = tmp_path / "receipt.json.sig"
    main(_run_args(out, private, adapter="trimgate.demo:leaky_adapter"))

    tampered = out.read_text(encoding="utf-8").replace('"verdict":"fail"', '"verdict":"pass"')
    out.write_text(tampered, encoding="utf-8")

    verify_code = main(["verify", str(out), "--sig", str(sig), "--public", str(public)])
    assert verify_code != 0


def test_verify_rejects_receipt_signed_by_untrusted_key_when_pinned(tmp_path):
    # Attacker signs their own forged PASS with their own keypair.
    attacker_priv, attacker_pub = tmp_path / "att.pem", tmp_path / "att.pub"
    main(["keygen", "--private", str(attacker_priv), "--public", str(attacker_pub)])
    out, sig = tmp_path / "receipt.json", tmp_path / "receipt.json.sig"
    main(_run_args(out, attacker_priv))

    # The trusted signer's fingerprint (what a verifier would pin out-of-band).
    trusted_priv, _ = _keypair(tmp_path)
    trusted_fp = key_fingerprint(load_private_key(trusted_priv.read_bytes()).public_key())

    # Bare verify with the attacker's own key passes (tamper-evidence only)...
    assert main(["verify", str(out), "--sig", str(sig), "--public", str(attacker_pub)]) == 0
    # ...but pinning the trusted signer rejects the forgery.
    code = main(
        [
            "verify",
            str(out),
            "--sig",
            str(sig),
            "--public",
            str(attacker_pub),
            "--expect-fingerprint",
            trusted_fp,
        ]
    )
    assert code != 0
