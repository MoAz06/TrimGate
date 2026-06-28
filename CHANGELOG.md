# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Deterministic core: access-matrix, labeled corpus, probe/probeset (stable hash),
  binary PASS/LEAK engine, and runner.
- `trimgate` CLI: `run`, `diff` (trim gap), `keygen`, `verify`.
- pytest plugin (`pytest --trimgate`) collecting `*.trimgate.yaml` suites into one
  test node per probe.
- Ed25519 signed receipts with a canonical (JCS-subset) JSON form. The signed
  payload binds the adapter spec, a timestamp, a nonce, and the signer key
  fingerprint; `verify --expect-fingerprint` pins the trusted signer.
- Azure AI Search + Entra reference adapter behind the `[azure]` extra, with a
  hardened OData filter (per-group `eq`; rejection of unsafe group ids and unsafe
  field names; empty-group fail-close; audit-sized top-k) and a live filter-shape
  smoke test.
- PEP 561 `py.typed`, CI jobs for the azure extra and a build/install-from-wheel
  smoke test, coverage gate, `SECURITY.md`, `CONTRIBUTING.md`.

### Security

- Reject duplicate chunk-IDs in the corpus (a public copy of a secret id could
  otherwise authorize the secret — a false pass on a real leak).
- Validate matrix/corpus at load (scalar-where-list, dangling group references,
  malformed rows) so a config typo cannot silently produce a green run.
- A run that audited nothing (zero probes, or every probe skipped) is a hard
  error, not a pass.
- `trimgate verify` exits non-zero for a validly-signed receipt whose verdict is
  not `pass`, and warns when the signer is not pinned with `--expect-fingerprint`.
- `canonical_json` rejects floats and non-finite values.
- `load_corpus` rejects non-string `chunk_id`/`label` and duplicate JSON keys.
- Strict base64 decoding of signatures.

### Notes

Pre-1.0: schema, receipt format, and CLI may change. See the README "Limitations"
section for what the auditor does and does not catch.
