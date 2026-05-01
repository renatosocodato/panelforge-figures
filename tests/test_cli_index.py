"""CliRunner tests for `figures index emit|validate` (Wave 1) and
`figures intake` (Wave 2) — closes the soak-test gap on Click dispatch."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from panelforge_figures.cli import main


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_figures_index_emit_writes_to_tmp_path(
    runner: CliRunner, tmp_path: Path,
) -> None:
    out = tmp_path / "test_index.json"
    result = runner.invoke(main, ["index", "emit", "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert out.is_file()
    data = json.loads(out.read_text())
    assert "index_meta" in data
    assert data["index_meta"]["n_recipes"] >= 107


def test_figures_index_emit_no_tags_flag(
    runner: CliRunner, tmp_path: Path,
) -> None:
    out = tmp_path / "test_index_no_tags.json"
    result = runner.invoke(main, ["index", "emit", "--out", str(out), "--no-tags"])
    assert result.exit_code == 0, result.output
    data = json.loads(out.read_text())
    assert data["index_meta"]["tags_enabled"] is False
    # All recipes must carry empty tags dict in Wave-1 mode.
    for mod in data["modalities"]:
        for rec in mod["recipes"]:
            assert rec["tags"] == {}, (
                f"Wave-1 recipe should have empty tags; "
                f"{mod['name']}.{rec['name']} has {rec['tags']}"
            )


def test_figures_index_emit_default_is_wave2(
    runner: CliRunner, tmp_path: Path,
) -> None:
    out = tmp_path / "test_index_default.json"
    result = runner.invoke(main, ["index", "emit", "--out", str(out)])
    assert result.exit_code == 0, result.output
    data = json.loads(out.read_text())
    # Default (no --no-tags flag) emits Wave-2 mode.
    assert data["index_meta"]["tags_enabled"] is True
    assert "scoring_rubric" in data
    assert "intake_questions" in data


def test_figures_index_validate_passes_on_committed_index(
    runner: CliRunner,
) -> None:
    """The committed `recipes_index.json` must always validate against
    the schema and the live registry."""
    result = runner.invoke(main, ["index", "validate"])
    assert result.exit_code == 0, result.output
    assert "valid" in result.output


def test_figures_index_validate_fails_on_missing_file(
    runner: CliRunner, tmp_path: Path,
) -> None:
    nope = tmp_path / "nonexistent.json"
    result = runner.invoke(main, ["index", "validate", "--path", str(nope)])
    assert result.exit_code != 0
    assert "not found" in result.output


def test_figures_index_validate_fails_on_invalid_json(
    runner: CliRunner, tmp_path: Path,
) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{ not valid json }")
    result = runner.invoke(main, ["index", "validate", "--path", str(bad)])
    assert result.exit_code != 0
    assert "not valid JSON" in result.output


def test_figures_index_validate_detects_orphan(
    runner: CliRunner, tmp_path: Path,
) -> None:
    """Index with a recipe that doesn't exist in the registry should fail."""
    # Start from a valid index.
    repo_root = Path(__file__).resolve().parents[1]
    real = json.loads((repo_root / "recipes_index.json").read_text())
    # Inject an orphan recipe.
    real["modalities"][0]["recipes"].append({
        "name": "orphan_recipe_does_not_exist",
        "path": "panelforge_figures.recipes.fake.orphan.render",
        "contract": "OrphanInput",
        "family": "matrix",
        "answers_question": "Where is the orphan?",
        "required_fields": ["foo"],
        "optional_fields": [],
        "alternatives_in_modality": [],
        "file_format_hints": [],
        "n_points_typical": "",
        "gallery_png": "docs/gallery/fake/orphan.png",
        "example_manifest": None,
        "tags": {},
    })
    bad = tmp_path / "with_orphan.json"
    bad.write_text(json.dumps(real, indent=2))
    result = runner.invoke(main, ["index", "validate", "--path", str(bad)])
    assert result.exit_code != 0
    assert "not registered" in result.output or "orphan" in result.output.lower()
