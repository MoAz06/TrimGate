"""TrimGate: deterministic, test-time auditor for RAG access-control trimming.

v1 verdict is binary PASS or LEAK: for every (identity, probe) the set of
chunk-IDs a RAG pipeline surfaces must be a subset of that identity's authorized
chunk-set, derived from the access-matrix. Zero LLM in the trust path.

See the reconciled v1 contract (handoff doc, section 0) for the normative shapes.
"""

__version__ = "0.0.1"
