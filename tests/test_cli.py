import pathlib

from trimgate.cli import main

QS = pathlib.Path(__file__).resolve().parents[1] / "examples" / "quickstart"
GOLDEN = pathlib.Path(__file__).resolve().parent / "golden"


def _args(adapter: str, command: str = "run") -> list[str]:
    return [
        command,
        "--adapter",
        adapter,
        "--matrix",
        str(QS / "access-matrix.yaml"),
        "--corpus",
        str(QS / "corpus.labeled.jsonl"),
        "--probes",
        str(QS / "probes.yaml"),
    ]


def test_cli_run_passes_on_clean_adapter(capsys):
    code = main(_args("trimgate.demo:clean_adapter"))
    assert code == 0
    assert "PASS" in capsys.readouterr().out


def test_cli_run_fails_on_leaky_adapter(capsys):
    code = main(_args("trimgate.demo:leaky_adapter"))
    assert code == 1
    out = capsys.readouterr().out
    assert "c-salary" in out  # the leaked chunk is named in the output


def test_cli_diff_emits_trim_gap_and_fails(capsys):
    code = main(_args("trimgate.demo:leaky_adapter", command="diff"))
    assert code == 1
    out = capsys.readouterr().out
    assert "bob" in out
    assert "c-salary" in out


def test_cli_diff_is_empty_and_passes_on_clean_adapter(capsys):
    code = main(_args("trimgate.demo:clean_adapter", command="diff"))
    assert code == 0


def test_cli_run_out_writes_canonical_receipt_and_markdown(tmp_path, capsys):
    out = tmp_path / "receipt.json"
    md = tmp_path / "receipt.md"
    code = main(_args("trimgate.demo:leaky_adapter") + ["--out", str(out), "--report-md", str(md)])
    assert code == 1

    golden = (GOLDEN / "receipt_leaky.json").read_text(encoding="utf-8").rstrip("\n")
    assert out.read_text(encoding="utf-8").rstrip("\n") == golden
    assert "c-salary" in md.read_text(encoding="utf-8")
