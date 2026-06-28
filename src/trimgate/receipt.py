"""The signed receipt (section 0): one deterministic, replayable audit artifact.

build_receipt() produces the canonical receipt payload (schema trimgate/receipt@1)
from a run. canonical_json() serializes it with sorted keys and no insignificant
whitespace, and REJECTS floats and non-finite values. This is a JCS-COMPATIBLE
SUBSET, not a full RFC 8785 implementation: it is byte-stable only for payloads of
strings, integers, lists, and objects. A second verifier MUST use this identical
serializer -- do not assume an arbitrary RFC 8785 library reproduces these bytes.
No fp_rate / block_rate: v1 is soundness-only.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from trimgate.runner import RunResult

SCHEMA = "trimgate/receipt@1"


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        digest.update(fh.read())
    return digest.hexdigest()


def build_receipt(
    result: RunResult, *, matrix_path: str, corpus_path: str, adapter: str
) -> dict[str, Any]:
    results = [
        {
            "probe_id": v.probe_id,
            "identity": v.identity,
            "probe_class": v.probe_class.value,
            "outcome": v.status.value,
            "surfaced_ids": sorted(v.surfaced_ids),
            "leaked_ids": sorted(v.leaked_ids),
        }
        for v in result.verdicts
    ]
    return {
        "schema": SCHEMA,
        "inputs": {
            "adapter": adapter,
            "matrix_sha256": _sha256_file(matrix_path),
            "corpus_sha256": _sha256_file(corpus_path),
            "probeset_sha256": result.probeset_hash,
        },
        "results": results,
        "summary": {
            "total_probes": len(result.verdicts),
            "leaked_probes": result.total_leaks,
            "error_probes": result.total_errors,
            "skipped_probes": result.total_skipped,
            "per_identity_leaks": dict(sorted(result.per_identity_leaks.items())),
        },
        "verdict": "pass" if result.passed else "fail",
    }


def seal_receipt(
    receipt: dict[str, Any], *, signed_at: str, nonce: str, key_fingerprint: str
) -> dict[str, Any]:
    """Wrap a receipt with provenance that goes INSIDE the signed bytes.

    Binding the signer key fingerprint, a timestamp, and a nonce makes the
    signature name which key signed it (verifiable against a pinned signer) and
    makes each run's bytes unique. Sealing also records the adapter via the
    receipt's inputs, so a signed PASS names which system it audited. Note: this
    is not replay protection -- stateless offline verification cannot detect a
    re-presented stale receipt; pin the signer and check signed_at out of band.
    """
    return {
        **receipt,
        "provenance": {
            "signed_at": signed_at,
            "nonce": nonce,
            "key_fingerprint": key_fingerprint,
        },
    }


def _reject_floats(value: object) -> None:
    # bool is an int subclass and is fine; floats (incl. inf/nan) are not portable.
    if isinstance(value, float):
        raise ValueError(f"canonical_json does not support floats: {value!r}")
    if isinstance(value, dict):
        for v in value.values():
            _reject_floats(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            _reject_floats(v)


def canonical_json(receipt: dict[str, Any]) -> str:
    _reject_floats(receipt)
    return json.dumps(
        receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def to_markdown(receipt: dict[str, Any]) -> str:
    summary = receipt["summary"]
    verdict = receipt["verdict"].upper()
    lines = [
        "# TrimGate receipt",
        "",
        f"Verdict: **{verdict}**",
        "",
        f"- probes: {summary['total_probes']}",
        f"- leaked probes: {summary['leaked_probes']}",
        f"- error probes: {summary['error_probes']}",
    ]
    per_identity = summary["per_identity_leaks"]
    if per_identity:
        rendered = ", ".join(f"{ident}={count}" for ident, count in per_identity.items())
        lines.append(f"- per-identity leaks: {rendered}")

    leaks = [r for r in receipt["results"] if r["outcome"] == "leak"]
    if leaks:
        lines += ["", "## Leaks"]
        for r in leaks:
            leaked = ", ".join(r["leaked_ids"])
            lines.append(f"- {r['probe_id']} {r['identity']} {r['probe_class']}: {leaked}")

    return "\n".join(lines) + "\n"
