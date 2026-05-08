"""Tests for provenance × reproducibility integration."""
from __future__ import annotations

from pathlib import Path

from panelforge_figures.manifest.provenance import (
    PROVENANCE_SCHEMA_VERSION,
    ProvenanceRecord,
    build_provenance,
    load_provenance_json,
    write_provenance_json,
)


def test_provenance_schema_bumped_to_1_1():
    assert PROVENANCE_SCHEMA_VERSION == "1.1.0"


def test_provenance_optional_lock_field_default_none(tmp_path: Path):
    """Existing provenance build paths still work; lock is optional."""
    fig = tmp_path / "fig.png"
    fig.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 50)
    recipe = tmp_path / "rec.py"
    recipe.write_text("# stub\n")

    rec = build_provenance(
        figure_path=fig,
        recipe_full_name="x.y",
        recipe_module_path=recipe,
        panelforge_version="2.2.0",
        panelforge_git_commit="uncommitted",
        data_files=[],
    )
    assert rec.provenance_lock is None


def test_provenance_with_lock_round_trip(tmp_path: Path):
    """build_provenance accepts a provenance_lock dict; round-trips."""
    fig = tmp_path / "fig.png"
    fig.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 50)
    recipe = tmp_path / "rec.py"
    recipe.write_text("# stub\n")

    lock_dict = {"schema_version": "1.0.0", "panelforge_version": "2.2.0"}
    rec = build_provenance(
        figure_path=fig,
        recipe_full_name="x.y",
        recipe_module_path=recipe,
        panelforge_version="2.2.0",
        panelforge_git_commit="uncommitted",
        data_files=[],
        provenance_lock=lock_dict,
    )
    assert rec.provenance_lock == lock_dict

    out = tmp_path / "prov.json"
    write_provenance_json(rec, out_path=out)
    loaded = load_provenance_json(out)
    assert loaded.provenance_lock == lock_dict


def test_old_provenance_loads_without_lock_field(tmp_path: Path):
    """A provenance.json without a provenance_lock field loads cleanly
    (lock defaults to None) — backwards-compatible."""
    out = tmp_path / "old.json"
    # Mock an old provenance file without the lock field
    import json
    out.write_text(json.dumps({
        "schema_version": "1.0.0",
        "figure_path": "x",
        "figure_sha256": "0" * 64,
        "rendered_at": "2026-01-01T00:00:00Z",
        "recipe": {"full_name": "x.y", "module_sha": "0" * 40,
                    "module_path": "y.py", "panelforge_version": "1.6.1",
                    "panelforge_git_commit": "uncommitted"},
        "data": {"sources": [], "column_mapping": {}},
    }))
    loaded = load_provenance_json(out)
    assert loaded.provenance_lock is None


def test_provenance_lock_omitted_from_json_when_none(tmp_path: Path):
    """When provenance_lock is None, the field should NOT appear in the
    serialized JSON — sidecars stay minimal/backwards-compatible."""
    fig = tmp_path / "fig.png"
    fig.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 50)
    recipe = tmp_path / "rec.py"
    recipe.write_text("# stub\n")

    rec = build_provenance(
        figure_path=fig,
        recipe_full_name="x.y",
        recipe_module_path=recipe,
        panelforge_version="2.2.0",
        panelforge_git_commit="uncommitted",
        data_files=[],
    )
    out = tmp_path / "prov.json"
    write_provenance_json(rec, out_path=out)
    import json
    loaded_raw = json.loads(out.read_text(encoding="utf-8"))
    assert "provenance_lock" not in loaded_raw


def test_provenance_lock_roundtrip_preserves_nested_dict(tmp_path: Path):
    """Nested lock structure (env + data + RNG) survives a full
    write/load cycle byte-identically."""
    fig = tmp_path / "fig.png"
    fig.write_bytes(b"\x89PNG\r\n\x1a\n" + b"z" * 50)
    recipe = tmp_path / "rec.py"
    recipe.write_text("# stub\n")

    lock_dict = {
        "schema_version": "1.0.0",
        "panelforge_version": "2.2.0",
        "environment": {
            "python_version": "3.12.12",
            "platform": "darwin",
            "matplotlib_version": "3.9.0",
        },
        "rng_seeds": {
            "numpy_seed": 42,
            "python_random_seed": 43,
            "torch_seed": None,
            "hypothesis_seed": None,
        },
        "data_files": [
            {"path": "data/a.csv", "sha256": "a" * 64, "n_bytes": 128},
        ],
        "uv_lock_path": "uv.lock",
        "uv_lock_sha256": "b" * 64,
    }
    rec = build_provenance(
        figure_path=fig,
        recipe_full_name="x.y",
        recipe_module_path=recipe,
        panelforge_version="2.2.0",
        panelforge_git_commit="uncommitted",
        data_files=[],
        provenance_lock=lock_dict,
    )
    out = tmp_path / "prov.json"
    write_provenance_json(rec, out_path=out)
    loaded = load_provenance_json(out)
    assert loaded.provenance_lock == lock_dict
    assert loaded.provenance_lock["rng_seeds"]["numpy_seed"] == 42
    assert loaded.provenance_lock["data_files"][0]["sha256"] == "a" * 64


def test_provenance_record_dataclass_field_default(tmp_path: Path):
    """Constructing a ProvenanceRecord directly without a lock field
    still works — default is None."""
    rec = ProvenanceRecord(
        schema_version=PROVENANCE_SCHEMA_VERSION,
        figure_path="fig.png",
        figure_sha256="0" * 64,
        rendered_at="2026-01-01T00:00:00Z",
        recipe={"full_name": "x.y"},
        data={"sources": [], "column_mapping": {}},
    )
    assert rec.provenance_lock is None
