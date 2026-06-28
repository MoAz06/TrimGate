"""The signed receipt (section 0): one deterministic, replayable audit artifact.

build_receipt() produces the canonical receipt payload (schema trimgate/receipt@1)
from a run. canonical_json() serializes it as a JSON Canonicalization Scheme
(RFC 8785) subset -- sorted keys, no insignificant whitespace; our payload has
only strings, arrays, objects, and integers, so this is byte-stable across
machines. The timestamp lives OUTSIDE this canonical payload so the bytes that
get signed (Week 3) are reproducible. No fp_rate / block_rate: v1 is
soundness-only.
"""

from __future__ import annotations

import hashlib
import json

from trimgate.engine import Outcome
from trimgate.runner import RunResult

SCHEMA = "trimgate/receipt@1"


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        digest.update(fh.read())
    return digest.hexdigest()


def build_receipt(result: RunResult, *, matrix_path: str, corpus_path: str) -> dict:
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
            "matrix_sha256": _sha256_file(matrix_path),
            "corpus_sha256": _sha256_file(corpus_path),
            "probeset_sha256": result.probeset_hash,
        },
        "results": results,
        "summary": {
            "total_probes": len(result.verdicts),
            "leaked_probes": result.total_leaks,
            "error_probes": result.total_errors,
            "per_identity_leaks": dict(sorted(result.per_identity_leaks.items())),
        },
        "verdict": "pass" if result.passed else "fail",
    }


def canonical_json(receipt: dict) -> str:
    return json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def to_markdown(receipt: dict) -> str:
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
