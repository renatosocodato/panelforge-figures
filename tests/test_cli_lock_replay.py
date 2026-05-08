"""Tests for the figures lock + figures replay CLI commands."""
from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from panelforge_figures.cli import main


def test_lock_writes_default_path(tmp_path: Path):
    runner = CliRunner()
    out = tmp_path / "lock.json"
    result = runner.invoke(main, [
        "lock", "--project-root", str(tmp_path),
        "--output", str(out),
    ])
    assert result.exit_code == 0, result.output
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["schema_version"] == "1.0.0"
    assert data["panelforge_version"]


def test_lock_with_data_file(tmp_path: Path):
    df = tmp_path / "x.csv"
    df.write_text("a,b\n1,2\n")
    out = tmp_path / "lock.json"
    runner = CliRunner()
    result = runner.invoke(main, [
        "lock", "--project-root", str(tmp_path),
        "--output", str(out),
        "--data-file", str(df),
    ])
    assert result.exit_code == 0, result.output
    data = json.loads(out.read_text())
    assert len(data["data_files"]) == 1


def test_lock_with_figure(tmp_path: Path):
    fig = tmp_path / "f.png"
    fig.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 50)
    out = tmp_path / "lock.json"
    runner = CliRunner()
    result = runner.invoke(main, [
        "lock", "--project-root", str(tmp_path),
        "--output", str(out),
        "--figure-path", str(fig),
    ])
    assert result.exit_code == 0
    data = json.loads(out.read_text())
    assert data["figure_sha256"]


def test_replay_succeeds_on_matching_env(tmp_path: Path):
    """Build a lock; replay it; should report no drift (same env)."""
    out = tmp_path / "lock.json"
    runner = CliRunner()
    runner.invoke(main, [
        "lock", "--project-root", str(tmp_path),
        "--output", str(out),
    ])
    result = runner.invoke(main, [
        "replay", str(out),
        "--workdir", str(tmp_path),
    ])
    assert result.exit_code == 0
    assert "matches" in result.output.lower()


def test_replay_fails_on_missing_lock(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(main, [
        "replay", str(tmp_path / "missing.json"),
    ])
    assert result.exit_code != 0


def test_replay_detects_drifted_python_version(tmp_path: Path):
    """Hand-craft a lock with a different python_version; replay flags drift."""
    lock_data = {
        "schema_version": "1.0.0",
        "created_at": "2026-01-01T00:00:00Z",
        "panelforge_version": "2.2.0",
        "panelforge_git_commit": "uncommitted",
        "panelforge_git_dirty": False,
        "environment": {
            "python_version": "3.99.99",  # impossible version → drift
            "python_executable": "/x",
            "platform": "x",
            "machine": "x",
            "blas_info": {},
            "locale": {"LANG": "", "LC_ALL": "", "LC_CTYPE": "", "TZ": ""},
            "cpu_count": 1,
        },
        "rng_seeds": {"numpy_seed": None, "python_random_seed": None,
                       "torch_seed": None, "hypothesis_seed": None},
        "data_files": [],
        "uv_lock_path": None,
        "uv_lock_sha256": None,
        "pip_freeze": [],
        "figure_sha256": None,
    }
    lp = tmp_path / "drift.json"
    lp.write_text(json.dumps(lock_data))

    runner = CliRunner()
    result = runner.invoke(main, [
        "replay", str(lp),
        "--workdir", str(tmp_path),
    ])
    assert result.exit_code != 0
    assert "drift" in result.output.lower()
