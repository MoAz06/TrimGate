"""TrimGate pytest plugin (auto-discovered via the pytest11 entry point).

Opt-in: inert unless `--trimgate` is passed, so installing TrimGate never changes
a downstream project's exit codes by accident. When active, every
`*.trimgate.yaml` file is collected as an access-control suite: one test node per
probe, failing on a LEAK or a fail-closed ERROR, skipping when a probe needs an
adapter method the host did not implement.

A `*.trimgate.yaml` file looks like::

    adapter: myapp.tests:make_adapter      # MODULE:ATTR (class or factory)
    matrix: security/access-matrix.yaml    # relative to this file, or absolute
    corpus: security/corpus.labeled.jsonl
    probes:
      - {id: P-001, identity: alice, probe_class: retrieval, query: "..."}
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

import pytest
import yaml

from trimgate.adapter import RagAdapter, resolve_adapter
from trimgate.corpus import Corpus, load_corpus
from trimgate.engine import Outcome, Verdict, evaluate
from trimgate.matrix import AccessMatrix, load_matrix
from trimgate.probe import Probe, build_probes

if TYPE_CHECKING:
    from _pytest.config.argparsing import Parser


class TrimGateLeak(Exception):
    """A probe surfaced a chunk the identity is not authorized to see."""


class TrimGateError(Exception):
    """A probe could not be evaluated soundly (fail-closed): adapter failure,
    unknown identity, or an unclassifiable surfaced chunk. Distinct from a leak,
    mirroring the CLI's exit-code split (1 = leak, 2 = error)."""


def pytest_addoption(parser: Parser) -> None:
    group = parser.getgroup("trimgate")
    group.addoption(
        "--trimgate",
        action="store_true",
        default=False,
        help="collect *.trimgate.yaml files as TrimGate access-control probes",
    )


def pytest_collect_file(file_path: pathlib.Path, parent: pytest.Collector) -> TrimGateFile | None:
    if parent.config.getoption("trimgate") and file_path.name.endswith(".trimgate.yaml"):
        return TrimGateFile.from_parent(parent, path=file_path)
    return None


class TrimGateFile(pytest.File):
    def collect(self) -> Iterator[TrimGateItem]:
        data = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        adapter = resolve_adapter(data["adapter"])
        matrix = load_matrix(self._resolve(data["matrix"]))
        corpus = load_corpus(self._resolve(data["corpus"]))
        for probe in build_probes(data.get("probes") or []):
            yield TrimGateItem.from_parent(
                self,
                name=probe.id,
                probe=probe,
                adapter=adapter,
                matrix=matrix,
                corpus=corpus,
            )

    def _resolve(self, value: str) -> str:
        path = pathlib.Path(value)
        return str(path if path.is_absolute() else self.path.parent / path)


class TrimGateItem(pytest.Item):
    def __init__(
        self,
        *,
        probe: Probe,
        adapter: RagAdapter,
        matrix: AccessMatrix,
        corpus: Corpus,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._probe = probe
        self._adapter = adapter
        self._matrix = matrix
        self._corpus = corpus

    def runtest(self) -> None:
        verdict = evaluate(self._probe, self._adapter, self._matrix, self._corpus)
        if verdict.status is Outcome.LEAK:
            raise TrimGateLeak(_leak_message(verdict))
        if verdict.status is Outcome.ERROR:
            raise TrimGateError(f"ERROR ({self._probe.id}): {verdict.detail}")
        if verdict.status is Outcome.SKIPPED:
            pytest.skip(verdict.detail or f"{self._probe.id} skipped")

    def reportinfo(self) -> tuple[pathlib.Path, int, str]:
        return self.path, 0, f"trimgate: {self._probe.id} ({self._probe.identity})"


def _leak_message(verdict: Verdict) -> str:
    leaked = ", ".join(sorted(verdict.leaked_ids))
    return (
        f"LEAK ({verdict.probe_id}): identity {verdict.identity!r} "
        f"retrieved unauthorized chunk(s): {leaked}"
    )
