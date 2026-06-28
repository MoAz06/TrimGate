"""Demo adapter factories for the quickstart seed (examples/quickstart).

These model a host RAG system under test. `clean_adapter` trims correctly for
every quickstart probe; `leaky_adapter` reproduces a real ACL-drift failure where
bob's retrieval and direct-fetch surface the finance salary chunk he may not see.
Both are constructible with no arguments so the CLI can reference them as
`trimgate.demo:clean_adapter` / `trimgate.demo:leaky_adapter`.

The adapter is the system under test; it is authored independently of the
access-matrix. TrimGate's job is to catch when the two disagree.
"""

from __future__ import annotations

from trimgate.fake import FakeAdapter

_BOB_SALARY_QUERY = "what are the engineering salary bands?"
_CAROL_SALARY_QUERY = "what are the engineering salary bands?"


def clean_adapter() -> FakeAdapter:
    """Every probe stays inside the identity's authorized set: a PASS run."""
    return FakeAdapter(
        retrievals={
            ("alice", "what is the parental leave policy?"): ["c-parental"],
            ("bob", _BOB_SALARY_QUERY): ["c-readme"],  # correctly trimmed
            ("carol", _CAROL_SALARY_QUERY): ["c-salary"],  # carol may see fin-secret
        },
        fetches={
            ("bob", "doc-salary-bands"): [],  # correctly denied
        },
    )


def leaky_adapter() -> FakeAdapter:
    """ACL drift: bob's retrieval and direct-fetch leak the finance chunk."""
    return FakeAdapter(
        retrievals={
            ("alice", "what is the parental leave policy?"): ["c-parental"],
            ("bob", _BOB_SALARY_QUERY): ["c-readme", "c-salary"],  # LEAK
            ("carol", _CAROL_SALARY_QUERY): ["c-salary"],
        },
        fetches={
            ("bob", "doc-salary-bands"): ["c-salary"],  # LEAK
        },
    )
