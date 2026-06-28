"""The `trimgate` command-line interface.

`trimgate run` loads the access-matrix, labeled corpus, and probeset, resolves the
adapter (MODULE:ATTR, instantiated/called if callable), runs the deterministic
probe runner, prints a human-readable summary, and exits non-zero on any leak so
CI can gate on it. Exit codes: 0 = clean, 1 = leak detected, 2 = fail-closed
error (config/adapter), matching the handoff's contract.
"""

from __future__ import annotations

import argparse
import json
import secrets
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from trimgate.adapter import resolve_adapter
from trimgate.corpus import load_corpus
from trimgate.diff import trim_gap
from trimgate.engine import Outcome
from trimgate.matrix import load_matrix
from trimgate.probe import load_probeset
from trimgate.receipt import build_receipt, canonical_json, seal_receipt, to_markdown
from trimgate.runner import RunResult, run
from trimgate.signing import (
    generate_private_key,
    key_fingerprint,
    load_private_key,
    load_public_key,
    private_key_to_pem,
    public_key_to_pem,
    sign,
    verify,
)

_MARK = {
    Outcome.PASS: "[ ok ]",
    Outcome.LEAK: "[FAIL]",
    Outcome.ERROR: "[ERR ]",
    Outcome.SKIPPED: "[SKIP]",
}


def _print_summary(result: RunResult) -> None:
    for verdict in result.verdicts:
        line = (
            f"{_MARK[verdict.status]} {verdict.probe_id} "
            f"{verdict.identity} {verdict.probe_class.value}"
        )
        if verdict.status is Outcome.LEAK:
            line += "  LEAK: " + ", ".join(sorted(verdict.leaked_ids))
        elif verdict.detail:
            line += f"  {verdict.detail}"
        print(line)

    identities = len({v.identity for v in result.verdicts})
    verdict_word = "PASS" if result.passed else "FAIL"
    print(
        f"TrimGate: {identities} identities, {len(result.verdicts)} probes, "
        f"{result.total_leaks} leak(s), {result.total_errors} error(s), "
        f"{result.total_skipped} skipped == VERDICT: {verdict_word}"
    )
    if result.total_skipped:
        print(
            f"NOTE: {result.total_skipped} probe(s) SKIPPED (adapter lacks the method) "
            f"-- those access paths were NOT audited"
        )


def _execute(args: argparse.Namespace) -> RunResult:
    matrix = load_matrix(args.matrix)
    corpus = load_corpus(args.corpus)
    probeset = load_probeset(args.probes)
    adapter = resolve_adapter(args.adapter)
    return run(probeset, adapter, matrix, corpus)


def _exit_code(result: RunResult) -> int:
    if result.passed:
        return 0
    # 1 = leak; 2 = fail-closed error or a vacuous (zero-probe) run.
    return 1 if result.total_leaks else 2


def _cmd_run(args: argparse.Namespace) -> int:
    result = _execute(args)
    _print_summary(result)

    if args.out or args.report_md or args.sign:
        receipt = build_receipt(
            result, matrix_path=args.matrix, corpus_path=args.corpus, adapter=args.adapter
        )
        if args.report_md:
            Path(args.report_md).write_text(to_markdown(receipt), encoding="utf-8", newline="\n")
        if args.sign:
            if not args.out:
                raise SystemExit("--sign requires --out")
            if not args.key:
                raise SystemExit("--sign requires --key (an Ed25519 private key PEM)")
            private_key = load_private_key(Path(args.key).read_bytes())
            sealed = seal_receipt(
                receipt,
                signed_at=datetime.now(UTC).isoformat(),
                nonce=secrets.token_hex(16),
                key_fingerprint=key_fingerprint(private_key.public_key()),
            )
            canonical = canonical_json(sealed)
            Path(args.out).write_text(canonical + "\n", encoding="utf-8", newline="\n")
            signature = sign(canonical.encode("utf-8"), private_key)
            Path(args.out + ".sig").write_text(signature + "\n", encoding="utf-8", newline="\n")
        elif args.out:
            Path(args.out).write_text(
                canonical_json(receipt) + "\n", encoding="utf-8", newline="\n"
            )

    return _exit_code(result)


def _cmd_keygen(args: argparse.Namespace) -> int:
    private_key = generate_private_key()
    Path(args.private).write_bytes(private_key_to_pem(private_key))
    Path(args.public).write_bytes(public_key_to_pem(private_key.public_key()))
    print(f"wrote private key {args.private} and public key {args.public}")
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    canonical = canonical_json(receipt).encode("utf-8")
    sig_path = args.sig or (args.receipt + ".sig")
    signature = Path(sig_path).read_text(encoding="utf-8").strip()
    public_key = load_public_key(Path(args.public).read_bytes())

    if not verify(canonical, signature, public_key):
        print(f"INVALID: {args.receipt} signature does not verify (tampered or wrong key)")
        return 1

    # The signed payload binds the signer's key fingerprint; confirm the supplied
    # key actually signed it, and (if pinned) that it is the trusted signer.
    provenance = receipt.get("provenance") or {}
    declared = provenance.get("key_fingerprint")
    actual = key_fingerprint(public_key)
    if declared != actual:
        print(f"INVALID: {args.receipt} was not signed by the provided key (unsigned receipt?)")
        return 1
    if args.expect_fingerprint and args.expect_fingerprint != actual:
        print("INVALID: signer fingerprint does not match the pinned --expect-fingerprint")
        return 1

    # A valid signature over a FAIL receipt is still a fail: do not report it OK.
    verdict = receipt.get("verdict")
    if verdict != "pass":
        print(f"INVALID: signature valid, but the audit verdict is {verdict!r} (not pass)")
        return 1

    trust = "trusted (pinned)" if args.expect_fingerprint else "UNTRUSTED -- signer not pinned"
    print(
        f"OK: verdict=pass, signer {actual[:16]} [{trust}], "
        f"self-reported signed_at {provenance.get('signed_at')}"
    )
    return 0


def _cmd_diff(args: argparse.Namespace) -> int:
    result = _execute(args)
    gap = trim_gap(result)
    for identity in sorted(gap):
        print(f"{identity} improperly reachable: {', '.join(sorted(gap[identity]))}")

    if result.total_errors or not result.verdicts:
        # An errored or vacuous audit is NOT clean; never report "none" for it.
        print(
            f"trim gap: INCOMPLETE -- {result.total_errors} error(s) over "
            f"{len(result.verdicts)} probe(s); audit did not run cleanly"
        )
    elif not gap:
        print("trim gap: none -- every identity stayed inside its authorized set")
    return _exit_code(result)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trimgate")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="run a probeset against an adapter")
    _add_common_args(run_parser)
    run_parser.add_argument("--out", help="write the canonical JSON receipt to this path")
    run_parser.add_argument("--report-md", help="write a human-readable Markdown report")
    run_parser.add_argument("--sign", action="store_true", help="Ed25519-sign the receipt")
    run_parser.add_argument("--key", help="Ed25519 private key PEM (required with --sign)")
    run_parser.set_defaults(func=_cmd_run)

    diff_parser = sub.add_parser("diff", help="emit the per-identity trim gap")
    _add_common_args(diff_parser)
    diff_parser.set_defaults(func=_cmd_diff)

    keygen_parser = sub.add_parser("keygen", help="generate an Ed25519 signing keypair")
    keygen_parser.add_argument(
        "--private", required=True, help="output path for the private key PEM"
    )
    keygen_parser.add_argument("--public", required=True, help="output path for the public key PEM")
    keygen_parser.set_defaults(func=_cmd_keygen)

    verify_parser = sub.add_parser("verify", help="verify a signed receipt offline")
    verify_parser.add_argument("receipt", help="path to the receipt JSON")
    verify_parser.add_argument("--sig", help="path to the signature (default: <receipt>.sig)")
    verify_parser.add_argument("--public", required=True, help="path to the public key PEM")
    verify_parser.add_argument(
        "--expect-fingerprint", help="pin the trusted signer's key fingerprint"
    )
    verify_parser.set_defaults(func=_cmd_verify)

    args = parser.parse_args(argv)
    return int(args.func(args))


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--adapter", required=True, help="MODULE:ATTR adapter import path")
    parser.add_argument("--matrix", required=True, help="path to access-matrix YAML")
    parser.add_argument("--corpus", required=True, help="path to labeled-corpus JSONL")
    parser.add_argument("--probes", required=True, help="path to probes YAML")
