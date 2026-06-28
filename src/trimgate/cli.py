"""The `trimgate` command-line interface.

`trimgate run` loads the access-matrix, labeled corpus, and probeset, resolves the
adapter (MODULE:ATTR, instantiated/called if callable), runs the deterministic
probe runner, prints a human-readable summary, and exits non-zero on any leak so
CI can gate on it. Exit codes: 0 = clean, 1 = leak detected, 2 = fail-closed
error (config/adapter), matching the handoff's contract.
"""

from __future__ import annotations

import argparse
import importlib
from collections.abc import Sequence

from trimgate.corpus import load_corpus
from trimgate.diff import trim_gap
from trimgate.engine import Outcome
from trimgate.matrix import load_matrix
from trimgate.probe import load_probeset
from trimgate.receipt import build_receipt, canonical_json, to_markdown
from trimgate.runner import RunResult, run

_MARK = {
    Outcome.PASS: "[ ok ]",
    Outcome.LEAK: "[FAIL]",
    Outcome.ERROR: "[ERR ]",
    Outcome.SKIPPED: "[SKIP]",
}


def _resolve_adapter(spec: str) -> object:
    module_name, sep, attr = spec.partition(":")
    if not sep or not attr:
        raise SystemExit(f"--adapter must be MODULE:ATTR, got {spec!r}")
    module = importlib.import_module(module_name)
    obj = getattr(module, attr)
    return obj() if callable(obj) else obj


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
        f"{result.total_leaks} leak(s), {result.total_errors} error(s) "
        f"== VERDICT: {verdict_word}"
    )


def _execute(args: argparse.Namespace) -> RunResult:
    matrix = load_matrix(args.matrix)
    corpus = load_corpus(args.corpus)
    probeset = load_probeset(args.probes)
    adapter = _resolve_adapter(args.adapter)
    return run(probeset, adapter, matrix, corpus)


def _exit_code(result: RunResult) -> int:
    if result.passed:
        return 0
    return 1 if result.total_leaks else 2


def _cmd_run(args: argparse.Namespace) -> int:
    result = _execute(args)
    _print_summary(result)

    if args.out or args.report_md:
        receipt = build_receipt(result, matrix_path=args.matrix, corpus_path=args.corpus)
        if args.out:
            with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(canonical_json(receipt) + "\n")
        if args.report_md:
            with open(args.report_md, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(to_markdown(receipt))

    return _exit_code(result)


def _cmd_diff(args: argparse.Namespace) -> int:
    result = _execute(args)
    gap = trim_gap(result)
    if not gap:
        print("trim gap: none -- every identity stayed inside its authorized set")
    else:
        for identity in sorted(gap):
            print(f"{identity} improperly reachable: {', '.join(sorted(gap[identity]))}")
    return _exit_code(result)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trimgate")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="run a probeset against an adapter")
    _add_common_args(run_parser)
    run_parser.add_argument("--fail-on-leak", action="store_true", help="exit non-zero on leak")
    run_parser.add_argument("--out", help="write the canonical JSON receipt to this path")
    run_parser.add_argument("--report-md", help="write a human-readable Markdown report")
    run_parser.set_defaults(func=_cmd_run)

    diff_parser = sub.add_parser("diff", help="emit the per-identity trim gap")
    _add_common_args(diff_parser)
    diff_parser.set_defaults(func=_cmd_diff)

    args = parser.parse_args(argv)
    return int(args.func(args))


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--adapter", required=True, help="MODULE:ATTR adapter import path")
    parser.add_argument("--matrix", required=True, help="path to access-matrix YAML")
    parser.add_argument("--corpus", required=True, help="path to labeled-corpus JSONL")
    parser.add_argument("--probes", required=True, help="path to probes YAML")
