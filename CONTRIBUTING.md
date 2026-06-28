# Contributing to TrimGate

Thanks for your interest. TrimGate is a soundness-critical tool, so the bar for
trust-path changes is high: every change to the engine, runner, loaders, signing,
or adapters needs tests.

## Development setup

```console
python -m venv .venv
. .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -e ".[dev]"        # add ,azure to work on the Azure adapter
```

## Before you push

All of these must pass (CI enforces them):

```console
ruff check .
ruff format --check .
mypy
pytest --cov=trimgate --cov-branch -q
```

## Expectations

- **Test-driven.** Write the failing test first, especially for any trust-path
  change. A bug fix lands with a regression test that fails without the fix.
- **Fail closed.** Ambiguity (unknown id, malformed input, adapter error) must be
  an error, never a silent pass. New code must not introduce a false-pass path.
- **Conventional Commits** for messages (`feat:`, `fix:`, `docs:`, `test:`, ...).
- **Update the CHANGELOG** `Unreleased` section.
- **PR checklist:** tests pass, coverage holds, types clean, docs updated, and any
  new claim in the README is honest about what is and is not guaranteed.

## Corpus contributions

The evaluation corpus and examples are CC-BY-4.0 and must be fully synthetic — no
real PII, customer names, or third-party-copyrighted text.
