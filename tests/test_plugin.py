import pathlib

QS = pathlib.Path(__file__).resolve().parents[1] / "examples" / "quickstart"
MATRIX = (QS / "access-matrix.yaml").as_posix()
CORPUS = (QS / "corpus.labeled.jsonl").as_posix()

# Queries must match the keys the demo adapters were seeded with.
PARENTAL = "what is the parental leave policy?"
SALARY = "what are the engineering salary bands?"


def _suite_file(adapter: str) -> str:
    return (
        f"adapter: {adapter}\n"
        f"matrix: {MATRIX}\n"
        f"corpus: {CORPUS}\n"
        "probes:\n"
        f'  - {{id: P-ok, identity: alice, probe_class: retrieval, query: "{PARENTAL}"}}\n'
        f'  - {{id: P-leak, identity: bob, probe_class: retrieval, query: "{SALARY}"}}\n'
    )


def test_plugin_collects_one_node_per_probe_and_fails_the_leak(pytester):
    (pytester.path / "demo.trimgate.yaml").write_text(
        _suite_file("trimgate.demo:leaky_adapter"), encoding="utf-8"
    )

    result = pytester.runpytest("--trimgate")

    result.assert_outcomes(passed=1, failed=1)
    result.stdout.fnmatch_lines(["*c-salary*"])


def test_plugin_clean_adapter_all_pass(pytester):
    (pytester.path / "demo.trimgate.yaml").write_text(
        _suite_file("trimgate.demo:clean_adapter"), encoding="utf-8"
    )

    result = pytester.runpytest("--trimgate")

    result.assert_outcomes(passed=2)


def test_plugin_error_probe_fails_as_error_not_leak(pytester):
    # 'ghost' is not in the matrix -> fail-closed ERROR, not a LEAK.
    content = (
        "adapter: trimgate.demo:clean_adapter\n"
        f"matrix: {MATRIX}\n"
        f"corpus: {CORPUS}\n"
        "probes:\n"
        '  - {id: P-err, identity: ghost, probe_class: retrieval, query: "x"}\n'
    )
    (pytester.path / "err.trimgate.yaml").write_text(content, encoding="utf-8")

    result = pytester.runpytest("--trimgate")

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*TrimGateError*"])


def test_plugin_inert_without_flag(pytester):
    (pytester.path / "demo.trimgate.yaml").write_text(
        _suite_file("trimgate.demo:leaky_adapter"), encoding="utf-8"
    )

    result = pytester.runpytest()

    result.assert_outcomes(passed=0, failed=0)
