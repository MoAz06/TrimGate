# TrimGate

> the access-control unit test for enterprise RAG

[![CI](https://github.com/<owner>/trimgate/actions/workflows/ci.yml/badge.svg)](https://github.com/<owner>/trimgate/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/code-Apache--2.0-blue.svg)](LICENSE)
[![Corpus](https://img.shields.io/badge/corpus-CC--BY--4.0-green.svg)](LICENSES/CC-BY-4.0.txt)

<!-- Replace <owner> with your GitHub username/org once the repo is pushed. -->

TrimGate is a deterministic, test-time auditor that proves a Retrieval-Augmented
Generation pipeline only ever surfaces, for a given identity, chunks that
identity is authorized to see. It is an **auditor, not an enforcer**: it never
sits in the live request path. For every test identity and probe it asserts

```
retrieved(query, identity) is a subset of authorized(identity)
```

Any chunk outside the authorized set is a leak. A leak fails the run with a
non-zero exit code. There is no LLM and no randomness in the trust path: the
verdict is pure set arithmetic over a declared access-matrix and a labeled
corpus.

This is v1, built against the reconciled contract in the project handoff doc
(section 0). Status: deterministic core complete against a fake in-memory
adapter; Azure + Entra adapter and report signing come next.

## Quickstart

```console
pip install -e ".[dev]"

# Run the bundled quickstart against a deliberately leaky demo adapter.
# A leak always exits non-zero (1 = leak, 2 = fail-closed error), so it gates CI
# without any extra flag.
trimgate run \
  --adapter trimgate.demo:leaky_adapter \
  --matrix examples/quickstart/access-matrix.yaml \
  --corpus examples/quickstart/corpus.labeled.jsonl \
  --probes examples/quickstart/probes.yaml
# -> bob leaks the finance chunk; exit code 1

# Swap to trimgate.demo:clean_adapter for a passing run (exit 0).
```

The per-identity trim gap (which chunks an identity could improperly reach):

```console
trimgate diff --adapter trimgate.demo:leaky_adapter \
  --matrix examples/quickstart/access-matrix.yaml \
  --corpus examples/quickstart/corpus.labeled.jsonl \
  --probes examples/quickstart/probes.yaml
```

### As a pytest plugin

Drop a `*.trimgate.yaml` suite file next to your tests and run `pytest
--trimgate`. Each probe becomes one test node that fails on a leak:

```yaml
# security/quickstart.trimgate.yaml
adapter: myapp.tests:make_adapter      # MODULE:ATTR (class or factory)
matrix: security/access-matrix.yaml
corpus: security/corpus.labeled.jsonl
probes:
  - {id: P-001, identity: alice, probe_class: retrieval, query: "..."}
```

## License

Dual-licensed by artifact type:

- **Code** (`src/`, `tests/`) under **Apache-2.0** (see [LICENSE](LICENSE) and [NOTICE](NOTICE)).
- **Corpus / examples** under **CC-BY-4.0** (see [LICENSES/CC-BY-4.0.txt](LICENSES/CC-BY-4.0.txt)).
