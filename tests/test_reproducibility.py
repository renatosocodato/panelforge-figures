"""Tests for the reproducibility envelope (Elevation 3)."""
from __future__ import annotations

from pathlib import Path

import pytest

from panelforge_figures.manifest.reproducibility import (
    LOCK_SCHEMA_VERSION,
    EnvironmentSnapshot,
    ReproducibilityError,
    ReproducibilityLock,
    RNGSeeds,
    build_lock,
    load_lock,
    replay_lock,
    save_lock,
    verify_byte_identical,
)


# Cluster 1 — Lock build/save/load round-trip
def test_build_lock_captures_python_version(tmp_path: Path):
    lock = build_lock(project_root=tmp_path, panelforge_version="2.2.0")
    assert lock.environment.python_version
    assert lock.schema_version == LOCK_SCHEMA_VERSION

def test_lock_round_trip(tmp_path: Path):
    lock = build_lock(project_root=tmp_path, panelforge_version="2.2.0")
    out = tmp_path / "panelforge.lock.json"
    save_lock(lock, out)
    assert out.exists()
    loaded = load_lock(out)
    assert loaded.panelforge_version == "2.2.0"
    assert loaded.environment.python_version == lock.environment.python_version

def test_load_rejects_wrong_schema_version(tmp_path: Path):
    out = tmp_path / "bad.json"
    out.write_text('{"schema_version": "9.9.9"}')
    with pytest.raises(ReproducibilityError, match="schema_version"):
        load_lock(out)


# Cluster 2 — Data file hashing
def test_build_lock_hashes_data_files(tmp_path: Path):
    f = tmp_path / "data.csv"
    f.write_text("col1,col2\n1,2\n3,4\n")
    lock = build_lock(project_root=tmp_path, panelforge_version="2.2.0",
                       data_files=[f])
    assert len(lock.data_files) == 1
    assert lock.data_files[0].path == str(f)
    assert lock.data_files[0].n_bytes == len(f.read_bytes())
    # sha256 must be 64 hex chars
    assert len(lock.data_files[0].sha256) == 64

def test_build_lock_skips_missing_data_file(tmp_path: Path):
    """If a data_file path doesn't exist, it's silently skipped (warning,
    not raise)."""
    lock = build_lock(project_root=tmp_path, panelforge_version="2.2.0",
                       data_files=[tmp_path / "missing.csv"])
    assert len(lock.data_files) == 0


# Cluster 3 — Figure hashing
def test_build_lock_hashes_figure(tmp_path: Path):
    fig = tmp_path / "fig.png"
    fig.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 100)
    lock = build_lock(project_root=tmp_path, panelforge_version="2.2.0",
                       figure_path=fig)
    assert lock.figure_sha256 is not None
    assert len(lock.figure_sha256) == 64

def test_verify_byte_identical_matches(tmp_path: Path):
    f = tmp_path / "fig.png"
    f.write_bytes(b"\x89PNG\r\n\x1a\n" + b"y" * 100)
    import hashlib
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    assert verify_byte_identical(f, sha) is True
    assert verify_byte_identical(f, "0" * 64) is False


# Cluster 4 — uv.lock detection
def test_build_lock_detects_uv_lock(tmp_path: Path):
    (tmp_path / "uv.lock").write_text("# fake uv.lock\n[package]\n")
    lock = build_lock(project_root=tmp_path, panelforge_version="2.2.0")
    assert lock.uv_lock_path == "uv.lock"
    assert lock.uv_lock_sha256 is not None

def test_build_lock_falls_back_to_pip_freeze_without_uv_lock(tmp_path: Path):
    """When no uv.lock exists, pip_freeze is captured instead."""
    lock = build_lock(project_root=tmp_path, panelforge_version="2.2.0")
    assert lock.uv_lock_path is None
    # pip_freeze may be empty if pip freeze fails, but the field exists
    assert isinstance(lock.pip_freeze, tuple)


# Cluster 5 — RNG seeds
def test_rng_seeds_captured_explicitly():
    seeds = RNGSeeds(numpy_seed=42, python_random_seed=43, torch_seed=44, hypothesis_seed=45)
    assert seeds.numpy_seed == 42

def test_build_lock_with_explicit_seeds(tmp_path: Path):
    seeds = RNGSeeds(numpy_seed=42, python_random_seed=None,
                      torch_seed=None, hypothesis_seed=None)
    lock = build_lock(project_root=tmp_path, panelforge_version="2.2.0",
                       rng_seeds=seeds)
    assert lock.rng_seeds.numpy_seed == 42


# Cluster 6 — Git state
def test_build_lock_handles_non_git_dir(tmp_path: Path):
    """Outside a git repo: commit is 'uncommitted', dirty is False."""
    lock = build_lock(project_root=tmp_path, panelforge_version="2.2.0")
    assert lock.panelforge_git_commit == "uncommitted"
    assert lock.panelforge_git_dirty is False


# Cluster 7 — Replay (env match path)
def test_replay_with_matching_env_succeeds(tmp_path: Path):
    """Build a lock; replay against the same env; should report no drift."""
    lock = build_lock(project_root=tmp_path, panelforge_version="2.2.0")
    result = replay_lock(
        lock,
        workdir=tmp_path,
        recipe_full_name="some.recipe",
        contract_dict={},
    )
    assert result.success is True
    assert result.drift_diagnostics == {}

def test_replay_detects_python_version_drift(tmp_path: Path):
    """Build a lock with a fake old Python version; replay flags drift."""
    lock = build_lock(project_root=tmp_path, panelforge_version="2.2.0")
    # Inject drift: pretend the lock was built on Python 3.10
    drifted = ReproducibilityLock(
        **{**lock.__dict__,
           "environment": EnvironmentSnapshot(
               **{**lock.environment.__dict__, "python_version": "3.10.0"}
           )},
    )
    result = replay_lock(
        drifted,
        workdir=tmp_path,
        recipe_full_name="some.recipe",
        contract_dict={},
    )
    assert result.success is False
    assert "python_version" in result.drift_diagnostics
