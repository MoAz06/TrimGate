# TrimGate

> the access-control unit test for enterprise RAG

[![CI](https://github.com/<owner>/trimgate/actions/workflows/ci.yml/badge.svg)](https://github.com/<owner>/trimgate/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/code-Apache--2.0-blue.svg)](LICENSE)
[![Corpus](https://img.shields.io/badge/corpus-CC--BY--4.0-green.svg)](LICENSES/CC-BY-4.0.txt)

<!-- Replace <owner> with your GitHub username/org once the repo is pushed. -->

TrimGate is a deterministic, test-time auditor for Retrieval-Augmented Generation
pipelines. For each test identity and probe it checks

```
retrieved(query, identity) is a subset of authorized(identity)
```

where `authorized(identity)` is computed from a **declared** access-matrix, not
from the system under test. Any chunk outside the authorized set is a leak; a leak
fails the run with a non-zero exit code. There is no LLM and no randomness in the
trust path: the verdict is pure set arithmetic.

It is an **auditor, not an enforcer** — it never sits in the live request path. It
proves *conformance to the declared policy*, not that the policy itself is
correct, and it is only as good as the access-matrix and labeled corpus you give
it. That honesty is the point: the output is evidence for your auditor, never a
certificate. See [Limitations](#limitations) for what it does and does not catch.

This is v1, built against the reconciled contract in the project handoff doc
(section 0). Status: deterministic core, pytest plugin, signed receipts, and the
Azure + Entra adapter are implemented and exercised against a live Free-tier Azure
AI Search index (a filter-shape check — see [Limitations](#limitations)).

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

## Signed receipts

The receipt is serialized with a canonical JSON form (a JCS-compatible subset, not
a full RFC 8785 implementation — verifiers must use the bundled serializer).
Signing it with Ed25519 makes the verdict tamper-evident and verifiable offline:

```console
trimgate keygen --private signing.pem --public signing.pub

trimgate run --adapter ... --matrix ... --corpus ... --probes ... \
  --out receipt.json --sign --key signing.pem      # writes receipt.json + receipt.json.sig

# verify exits 0 only when the signature is valid AND the audit verdict is pass.
# Without --expect-fingerprint it prints an UNTRUSTED warning (tamper-evidence only):
trimgate verify receipt.json --public signing.pub
# Pin the trusted signer's fingerprint (printed by verify above) to enforce authenticity:
trimgate verify receipt.json --public signing.pub --expect-fingerprint <fp>
```

The signed payload binds the adapter spec, a timestamp, a nonce, and the signer's
key fingerprint, so a receipt names *which* system it audited, *when*, and *who*
signed it (and a zero-probe run is a hard error, not a pass). Editing a signed
receipt — e.g. flipping `fail` to `pass` — makes `verify` fail.

**Authenticity requires pinning.** Bare `verify` only proves the receipt was
signed by the holder of the supplied key; an adversary can sign their own forged
receipt with their own key. To prove the receipt came from a *trusted* signer, the
verifier must pin that signer's fingerprint via `--expect-fingerprint`, obtained
out-of-band. The public key is not trust on its own.

## Azure AI Search adapter

The reference adapter reproduces Azure AI Search + Entra security trimming: it
resolves an identity to its Entra group ids and applies the OData intersection
filter so only authorized chunks are retrieved. Install the optional extra:

```console
pip install "trimgate[azure]"
```

```python
from trimgate.adapters.azure import AzureSearchAdapter, make_search_client

adapter = AzureSearchAdapter(
    make_search_client(endpoint="https://<svc>.search.windows.net", index_name="<index>"),
    group_resolver=resolve_entra_groups,   # identity id -> [group object ids]
)
```

`make_search_client` defaults to `DefaultAzureCredential` (managed identity) on
Basic tier and above; the Free tier requires an API key (`AzureKeyCredential`).
The adapter is duck-typed against the search client, so it unit-tests with a fake
client and needs no live tenant. Group ids are validated (commas/quotes/control
characters are rejected) and the audit retrieves a large top-k so a low-ranked
unauthorized chunk cannot be truncated out of view. See
[docs/azure-setup.md](docs/azure-setup.md) for a live walkthrough.

## Limitations

TrimGate is deliberately scoped. It does **not** yet cover:

- **Policy shape.** The access-matrix is a flat `group -> labels` union. It cannot
  express deny rules, per-user exceptions, legal holds, or label hierarchy. If your
  real ACL uses those, TrimGate cannot represent the policy and would mis-audit the
  excepted documents — declare such cases out of scope rather than trusting a pass.
- **Retrieval shape.** The soundness check assumes single-stage retrieval over the
  full filtered candidate set. Rerankers, hybrid fusion, citation/answer
  post-processing, and small top-k windows can each hide a leak; the Azure adapter
  defaults to a large top-k but you must size it above what the filter can return.
- **Adapter fidelity.** The audit is only as faithful as the adapter. The reference
  Azure adapter *rebuilds* the production OData filter, so it best catches drift
  that lives outside that filter (e.g. stale index ACLs); an over-broad filter is
  caught only if the unauthorized chunks are actually surfaced (hence large top-k).
- **The live Azure example is a filter-shape smoke test**, not proof of real Entra
  enforcement: the seed tags and the `group_resolver` share invented ids, and on
  Free-tier key auth there is no identity-based enforcement in the loop. It proves
  the filter agrees with the matrix, not that production token-to-group resolution
  is correct.
- **Receipt authenticity needs out-of-band key pinning** (see above).

## License

Dual-licensed by artifact type:

- **Code** (`src/`, `tests/`) under **Apache-2.0** (see [LICENSE](LICENSE) and [NOTICE](NOTICE)).
- **Corpus / examples** under **CC-BY-4.0** (see [LICENSES/CC-BY-4.0.txt](LICENSES/CC-BY-4.0.txt)).
