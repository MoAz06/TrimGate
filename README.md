# TrimGate

> the access-control unit test for enterprise RAG

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
(section 0). Status: early build, deterministic core first (fake in-memory
adapter), Azure + Entra adapter later.

## License

Code under Apache-2.0.
