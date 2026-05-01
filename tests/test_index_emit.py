"""Tests for `recipes_index.json` emission (Wave 1).

Verifies:
  * `build_index()` is reachable, deterministic, and reflects the registry.
  * Every registered recipe is present in the index.
  * `index_meta` block carries the required keys.
  * `emit_index_json()` writes a file that round-trips through `json.loads`.
  * The Wave-1 `tags` block defaults to an empty dict per recipe (placeholder
    for Wave 2 tag enablement).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from panelforge_figures import __version__
from panelforge_figures.core.contract import (
    ensure_all_imported,
    list_recipes,
    registry_counts,
)
from panelforge_figures.manifest import (
    INDEX_SCHEMA_VERSION,
    build_index,
    emit_index_json,
)


def _force_built_at(monkeypatch) -> str:
    stamp = "2026-05-01T00:00:00Z"
    monkeypatch.setenv("PANELFORGE_BUILT_AT", stamp)
    return stamp


def test_build_index_returns_dict_with_meta() -> None:
    idx = build_index()
    assert isinstance(idx, dict)
    assert "index_meta" in idx
    meta = idx["index_meta"]
    for key in (
        "schema_version",
        "panelforge_version",
        "git_commit",
        "built_at",
        "n_recipes",
        "n_modalities",
        "tags_enabled",
    ):
        assert key in meta, f"index_meta missing key: {key}"
    assert meta["schema_version"] == INDEX_SCHEMA_VERSION
    assert meta["panelforge_version"] == __version__
    assert meta["tags_enabled"] is False


def test_build_index_counts_match_registry() -> None:
    ensure_all_imported()
    counts = registry_counts()
    idx = build_index()
    assert idx["index_meta"]["n_recipes"] == sum(counts.values())
    assert idx["index_meta"]["n_modalities"] == len(counts)


def test_every_registered_recipe_appears_in_index() -> None:
    ensure_all_imported()
    expected = {f"{e.metadata.modality}.{e.metadata.name}" for e in list_recipes()}
    idx = build_index()
    actual = set()
    for mod in idx["modalities"]:
        for rec in mod["recipes"]:
            actual.add(f"{mod['name']}.{rec['name']}")
    assert actual == expected, (
        f"index drift: {len(expected - actual)} missing, "
        f"{len(actual - expected)} orphan"
    )


def test_each_recipe_has_required_index_fields() -> None:
    idx = build_index()
    required = {
        "name",
        "path",
        "contract",
        "family",
        "answers_question",
        "required_fields",
        "optional_fields",
        "alternatives_in_modality",
        "file_format_hints",
        "gallery_png",
        "tags",
    }
    for mod in idx["modalities"]:
        for rec in mod["recipes"]:
            missing = required - set(rec.keys())
            assert not missing, (
                f"recipe {mod['name']}.{rec['name']} missing fields: {missing}"
            )


def test_tags_default_to_empty_dict_in_wave1() -> None:
    idx = build_index()
    for mod in idx["modalities"]:
        for rec in mod["recipes"]:
            assert rec["tags"] == {}, (
                f"Wave-1 tags should be empty; "
                f"{mod['name']}.{rec['name']} has {rec['tags']}"
            )


def test_wave2_blocks_absent_when_include_tags_false() -> None:
    idx = build_index(include_tags=False)
    assert "scoring_rubric" not in idx
    assert "intake_questions" not in idx


def test_wave2_blocks_present_when_include_tags_true() -> None:
    idx = build_index(include_tags=True)
    assert "scoring_rubric" in idx
    assert "intake_questions" in idx
    assert idx["index_meta"]["tags_enabled"] is True


def test_built_at_env_override(monkeypatch) -> None:
    stamp = _force_built_at(monkeypatch)
    idx = build_index()
    assert idx["index_meta"]["built_at"] == stamp


def test_git_commit_env_override(monkeypatch) -> None:
    monkeypatch.setenv("PANELFORGE_GIT_COMMIT", "deadbeef" * 5)
    idx = build_index()
    assert idx["index_meta"]["git_commit"] == "deadbeef" * 5


def test_emit_index_json_round_trips(tmp_path: Path, monkeypatch) -> None:
    _force_built_at(monkeypatch)
    out = tmp_path / "recipes_index.json"
    p = emit_index_json(out)
    assert p.exists()
    data = json.loads(out.read_text())
    assert data["index_meta"]["panelforge_version"] == __version__


def test_emit_index_json_is_deterministic(tmp_path: Path, monkeypatch) -> None:
    _force_built_at(monkeypatch)
    monkeypatch.setenv("PANELFORGE_GIT_COMMIT", "stable_commit_for_test")
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    emit_index_json(a)
    emit_index_json(b)
    assert a.read_bytes() == b.read_bytes()


def test_repo_root_index_matches_registry() -> None:
    """The committed `recipes_index.json` at repo root must agree with
    the live registry — guards against PRs that change recipes without
    regenerating the index.
    """
    repo_root = Path(__file__).resolve().parents[1]
    index_path = repo_root / "recipes_index.json"
    if not index_path.is_file():
        # Wave-1 hasn't shipped yet in this branch — tolerate.
        return
    ensure_all_imported()
    expected = {f"{e.metadata.modality}.{e.metadata.name}" for e in list_recipes()}
    on_disk = set()
    data = json.loads(index_path.read_text())
    for mod in data.get("modalities", []):
        for rec in mod.get("recipes", []):
            on_disk.add(f"{mod['name']}.{rec['name']}")
    assert on_disk == expected, (
        "recipes_index.json is stale: regenerate with "
        "`figures index emit` and commit the result"
    )


def test_panelforge_built_at_env_var_unset_falls_back_to_now(monkeypatch) -> None:
    monkeypatch.delenv("PANELFORGE_BUILT_AT", raising=False)
    idx = build_index()
    # ISO-8601 UTC; ends with 'Z'.
    assert idx["index_meta"]["built_at"].endswith("Z")
    # Must be a string of length 20 (e.g. 2026-05-01T00:00:00Z).
    assert len(idx["index_meta"]["built_at"]) == 20


def test_clean_env_no_panelforge_overrides() -> None:
    """Sanity: the env-var override hooks don't leak into normal runs."""
    # Make sure our test infrastructure isn't relying on stale env vars.
    if os.environ.get("PANELFORGE_BUILT_AT"):
        del os.environ["PANELFORGE_BUILT_AT"]
    if os.environ.get("PANELFORGE_GIT_COMMIT"):
        del os.environ["PANELFORGE_GIT_COMMIT"]
    idx = build_index()
    assert idx["index_meta"]["built_at"].endswith("Z")
