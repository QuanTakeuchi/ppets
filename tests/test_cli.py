"""
Tests for the headless entry point (main.py, HS5): the reference run is
unchanged, every input path is validated, and bad input exits with status 2
and a message instead of a traceback.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

import main as cli

REPO = Path(__file__).resolve().parent.parent
EXPECTED = (REPO / "evidence" / "hs5" / "main_expected.txt").read_text(encoding="utf-8").replace("\r\n", "\n")


def run_cli(argv):
    out = io.StringIO()
    config, generations = cli.resolve(cli.build_parser().parse_args(argv))
    cli.run(config, generations, out)
    return out.getvalue()


def test_default_run_matches_committed_reference():
    assert run_cli([]) == EXPECTED


def test_default_config_file_matches_reference():
    assert run_cli(["--config", str(REPO / "configs" / "default.json")]) == EXPECTED


def test_same_seed_same_trace_different_seed_different_trace():
    assert run_cli(["--seed", "7"]) == run_cli(["--seed", "7"])
    assert run_cli(["--seed", "7"]) != run_cli(["--seed", "8"])


def test_command_line_overrides_config_file(tmp_path):
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps({"seed": 7, "generations": 5}), encoding="utf-8")
    assert run_cli(["--config", str(cfg), "--seed", "42", "--generations", "50"]) == EXPECTED


def test_output_file_written_with_lf_endings(tmp_path):
    target = tmp_path / "trace.csv"
    assert cli.main(["--output", str(target)]) == 0
    assert target.read_bytes().decode("utf-8") == EXPECTED


@pytest.mark.parametrize(
    "argv, message",
    [
        (["--width", "1"], "width and height must both be >= 2"),
        (["--prey-density", "0.8", "--predator-density", "0.3"], "must not exceed 1.0"),
        (["--generations", "0"], "generations must be an integer"),
        (["--config", "does_not_exist.json"], "config file not found"),
    ],
)
def test_invalid_input_exits_2_with_message(argv, message, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(argv)
    assert exc.value.code == 2
    assert message in capsys.readouterr().err


@pytest.mark.parametrize(
    "content, message",
    [
        ("{not json", "is not valid JSON"),
        ("[1, 2]", "must contain a JSON object"),
        ('{"width": "30"}', "width must be an integer"),
        ('{"width": 30.5}', "width must be an integer"),
        ('{"prey_density": "high"}', "prey_density must be a number"),
        ('{"toroidal": "yes"}', "toroidal must be true or false"),
        ('{"predator_densty": 0.1}', "unknown parameter 'predator_densty'"),
        ('{"generations": 2.5}', "generations must be an integer"),
    ],
)
def test_bad_config_file_reported_by_name(tmp_path, content, message, capsys):
    cfg = tmp_path / "bad.json"
    cfg.write_text(content, encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        cli.main(["--config", str(cfg)])
    assert exc.value.code == 2
    assert message in capsys.readouterr().err


def test_unwritable_output_reported(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--output", str(tmp_path / "missing_dir" / "trace.csv")])
    assert exc.value.code == 2
    assert "cannot write" in capsys.readouterr().err


def test_subprocess_error_has_no_traceback():
    proc = subprocess.run([sys.executable, "main.py", "--width", "1"], cwd=REPO, capture_output=True, text=True)
    assert proc.returncode == 2
    assert "Traceback" not in proc.stderr
