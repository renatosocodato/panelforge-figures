"""Tests for project-plugin discovery + loading (Sprint 2A — v1.10.0).

Covers:

* Single-file (directory) discovery: walks ``tests/fixtures/sample_plugin/
  panelforge_plugins/``, asserts the recipe lands in the registry.
* Entry-points discovery: monkeypatches ``importlib.metadata.entry_points``
  with a fake EP whose ``.load()`` imports the same fixture.
* Idempotence + reset semantics.
* Conflict resolution (duplicate ``{modality}.{name}`` is fail-fast).
* Disabled-plugin suppression.
* Bad-syntax / missing-recipe plugins → ``PluginLoadError``.
* CLI: ``figures plugins list`` / ``figures plugins describe``.

Each test isolates the global recipe registry + plugin state so tests
order-independent.  See ``_clean_plugin_state`` fixture.
"""

from __future__ import annotations

import sys
import textwrap
from collections.abc import Iterator
from pathlib import Path

import pytest
from click.testing import CliRunner

from panelforge_figures import plugins as plugins_mod
from panelforge_figures.cli import main as cli_main
from panelforge_figures.core import contract as core_contract
from panelforge_figures.plugins import (
    PluginConflictError,
    PluginInfo,
    PluginLoadError,
    discover_all_plugins,
    discover_directory_plugins,
    discover_entry_point_plugins,
    list_loaded_plugins,
    plugin_for_recipe,
    reset_plugin_state,
)

# ─────────────────────────── fixtures ───────────────────────────────────


SAMPLE_FIXTURE_DIR = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "sample_plugin"
    / "panelforge_plugins"
)


@pytest.fixture
def _clean_plugin_state() -> Iterator[None]:
    """Snapshot + restore both ``_LOADED_PLUGINS`` and the recipe registry.

    Plugins mutate the recipe registry at import time; tests need a
    clean slate to be order-independent.  Also drops any plugin module
    we may have inserted into ``sys.modules`` so re-import isn't a no-op.
    """
    saved_registry = dict(core_contract._REGISTRY)
    saved_plugins = dict(plugins_mod._LOADED_PLUGINS)
    saved_modules = {
        k: v for k, v in sys.modules.items()
        if k.startswith("panelforge_user_plugins")
    }
    try:
        # Start every test with no plugins loaded.
        reset_plugin_state()
        yield
    finally:
        # Restore the recipe registry — drop any keys we added, restore originals.
        core_contract._REGISTRY.clear()
        core_contract._REGISTRY.update(saved_registry)
        # Restore the plugin cache.
        plugins_mod._LOADED_PLUGINS.clear()
        plugins_mod._LOADED_PLUGINS.update(saved_plugins)
        # Drop any user-plugin modules we inserted.
        for k in list(sys.modules):
            if k.startswith("panelforge_user_plugins") and k not in saved_modules:
                sys.modules.pop(k, None)


@pytest.fixture
def parent_of_panelforge_plugins() -> Path:
    """The directory that *contains* ``panelforge_plugins/`` (= the project root)."""
    return SAMPLE_FIXTURE_DIR.parent


# ─────────────────────────── directory discovery ────────────────────────


def test_directory_plugin_discovers_and_loads(
    _clean_plugin_state: None, parent_of_panelforge_plugins: Path,
) -> None:
    """The fixture's `example_extras.py` should register one recipe."""
    plugins_dir = parent_of_panelforge_plugins / "panelforge_plugins"
    loaded = discover_directory_plugins(plugins_dir)

    assert len(loaded) == 1
    info = loaded[0]
    assert info.name == "example_extras"
    assert info.source == "directory"
    assert info.version == "0.1.0"
    assert info.module_path is not None
    assert info.module_path.name == "example_extras.py"
    assert info.discovered_recipes == ("example_extras.cohort_violin",)


def test_directory_plugin_recipe_lands_in_registry(
    _clean_plugin_state: None, parent_of_panelforge_plugins: Path,
) -> None:
    discover_directory_plugins(parent_of_panelforge_plugins / "panelforge_plugins")

    full_names = {
        f"{e.metadata.modality}.{e.metadata.name}"
        for e in core_contract.list_recipes()
    }
    assert "example_extras.cohort_violin" in full_names


def test_directory_plugin_underscore_files_skipped(
    _clean_plugin_state: None, tmp_path: Path,
) -> None:
    """Files starting with `_` (private helpers) should be skipped."""
    plugins_dir = tmp_path / "panelforge_plugins"
    plugins_dir.mkdir()
    (plugins_dir / "_helpers.py").write_text("raise RuntimeError('should not load')\n")

    loaded = discover_directory_plugins(plugins_dir)
    assert loaded == []


def test_directory_plugin_missing_dir_returns_empty(
    _clean_plugin_state: None, tmp_path: Path,
) -> None:
    """No directory → no plugins, no error (opt-in by presence)."""
    loaded = discover_directory_plugins(tmp_path / "does_not_exist")
    assert loaded == []


def test_directory_plugin_disabled_is_skipped(
    _clean_plugin_state: None, parent_of_panelforge_plugins: Path,
) -> None:
    plugins_dir = parent_of_panelforge_plugins / "panelforge_plugins"
    loaded = discover_directory_plugins(plugins_dir, disabled=("example_extras",))
    assert loaded == []
    # Nothing landed in the registry either.
    full_names = {
        f"{e.metadata.modality}.{e.metadata.name}"
        for e in core_contract.list_recipes()
    }
    assert "example_extras.cohort_violin" not in full_names


def test_bad_syntax_plugin_raises_plugin_load_error(
    _clean_plugin_state: None, tmp_path: Path,
) -> None:
    """A plugin with a SyntaxError must surface a PluginLoadError."""
    plugins_dir = tmp_path / "panelforge_plugins"
    plugins_dir.mkdir()
    (plugins_dir / "broken.py").write_text("def render( -- not valid python\n")

    with pytest.raises(PluginLoadError, match="broken"):
        discover_directory_plugins(plugins_dir)


# ─────────────────────────── entry_points discovery ─────────────────────


class _FakeEntryPoint:
    """Minimal stand-in for `importlib.metadata.EntryPoint`."""

    def __init__(self, name: str, target_module: str) -> None:
        self.name = name
        self.value = target_module
        self.group = "panelforge.plugins"
        self._target = target_module

    def load(self) -> object:
        # Force-import the plugin module by file path so the fixture
        # doesn't need to be on sys.path.  Simulates what `pkg_resources`
        # would do for an installed package.
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            self._target, str(SAMPLE_FIXTURE_DIR / "example_extras.py"),
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[self._target] = module
        spec.loader.exec_module(module)
        return module


def test_entry_points_plugin_loads_via_metadata(
    monkeypatch: pytest.MonkeyPatch, _clean_plugin_state: None,
) -> None:
    """A fake entry-point should be discoverable + register its recipe."""
    fake_ep = _FakeEntryPoint(
        name="example_extras_ep",
        target_module="panelforge_example_extras_ep_test",
    )

    def _fake_entry_points(*, group: str = "") -> list[_FakeEntryPoint]:
        if group == "panelforge.plugins":
            return [fake_ep]
        return []

    monkeypatch.setattr(
        "importlib.metadata.entry_points", _fake_entry_points,
    )
    try:
        loaded = discover_entry_point_plugins()
        assert len(loaded) == 1
        info = loaded[0]
        assert info.name == "example_extras_ep"
        assert info.source == "entry_points"
        assert info.discovered_recipes == ("example_extras.cohort_violin",)
    finally:
        # Drop the fake module so subsequent tests aren't tainted.
        sys.modules.pop("panelforge_example_extras_ep_test", None)


# ─────────────────────────── conflict resolution ────────────────────────


def test_duplicate_full_name_raises_conflict_error(
    _clean_plugin_state: None, tmp_path: Path,
    parent_of_panelforge_plugins: Path,
) -> None:
    """Two plugins registering the same `{modality}.{name}` → conflict."""
    # First, load the canonical fixture.
    discover_directory_plugins(
        parent_of_panelforge_plugins / "panelforge_plugins",
    )

    # Now build a duplicate plugin in a tmpdir.
    duplicate_dir = tmp_path / "panelforge_plugins"
    duplicate_dir.mkdir()
    duplicate = duplicate_dir / "duplicate.py"
    duplicate.write_text(textwrap.dedent('''
        from panelforge_figures.core import (
            RecipeContract, RecipeFamily, RecipeMetadata, register_recipe,
        )

        class _Inp(RecipeContract):
            x: list[float] = []

        _META = RecipeMetadata(
            name="cohort_violin",            # SAME as the fixture
            modality="example_extras",          # SAME as the fixture
            family=RecipeFamily.split_violin,
            answers_question="dup",
            required_fields=("x",),
        )

        @register_recipe(metadata=_META, contract=_Inp, demo_contract=lambda: _Inp())
        def render(contract, ax=None, **_):
            return ax
    '''))

    with pytest.raises(PluginConflictError, match="duplicate"):
        discover_directory_plugins(duplicate_dir)


# ─────────────────────────── state helpers ──────────────────────────────


def test_reset_plugin_state_clears_loaded(
    _clean_plugin_state: None, parent_of_panelforge_plugins: Path,
) -> None:
    discover_directory_plugins(
        parent_of_panelforge_plugins / "panelforge_plugins",
    )
    assert len(list_loaded_plugins()) == 1
    reset_plugin_state()
    assert list_loaded_plugins() == []


def test_discover_all_combines_both_paths(
    monkeypatch: pytest.MonkeyPatch, _clean_plugin_state: None,
    parent_of_panelforge_plugins: Path,
) -> None:
    """`discover_all_plugins` should merge entry-points + directory."""
    # Directory side: the canonical fixture.
    plugins_dir = parent_of_panelforge_plugins / "panelforge_plugins"

    # Entry-point side: empty (avoids conflict with the directory plugin).
    def _no_eps(*, group: str = "") -> list[_FakeEntryPoint]:
        return []

    monkeypatch.setattr("importlib.metadata.entry_points", _no_eps)
    loaded = discover_all_plugins(plugins_dir=plugins_dir)
    assert len(loaded) == 1
    assert loaded[0].name == "example_extras"


def test_plugin_for_recipe_returns_owner(
    _clean_plugin_state: None, parent_of_panelforge_plugins: Path,
) -> None:
    discover_directory_plugins(
        parent_of_panelforge_plugins / "panelforge_plugins",
    )
    assert plugin_for_recipe("example_extras.cohort_violin") == "example_extras"


def test_plugin_for_recipe_returns_none_for_catalog(
    _clean_plugin_state: None,
) -> None:
    """A catalog (non-plugin) recipe → `plugin_for_recipe` returns None."""
    # Do NOT call discover; just ask about a catalog recipe.
    core_contract.ensure_all_imported()
    catalog_full_names = [
        f"{e.metadata.modality}.{e.metadata.name}"
        for e in core_contract.list_recipes()
    ]
    assert catalog_full_names, "registry should hold catalog recipes"
    assert plugin_for_recipe(catalog_full_names[0]) is None


# ─────────────────────────── CLI surface ────────────────────────────────


def test_cli_plugins_list_help_exits_clean() -> None:
    """`figures plugins list --help` is the safest CLI happy-path."""
    r = CliRunner().invoke(cli_main, ["plugins", "list", "--help"])
    assert r.exit_code == 0
    assert "Usage:" in r.output


def test_cli_plugins_list_no_plugins(
    monkeypatch: pytest.MonkeyPatch, _clean_plugin_state: None, tmp_path: Path,
) -> None:
    """When no plugins are present, `figures plugins list` says so."""
    # Run from a directory with no `panelforge_plugins/`.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "importlib.metadata.entry_points",
        lambda *, group="": [],
    )
    r = CliRunner().invoke(cli_main, ["plugins", "list"])
    assert r.exit_code == 0, r.output
    assert "no plugins discovered" in r.output


def test_cli_plugins_list_shows_directory_plugin(
    monkeypatch: pytest.MonkeyPatch, _clean_plugin_state: None,
    parent_of_panelforge_plugins: Path,
) -> None:
    """Run from the fixture's parent so the dir scan finds example_extras."""
    monkeypatch.chdir(parent_of_panelforge_plugins)
    monkeypatch.setattr(
        "importlib.metadata.entry_points",
        lambda *, group="": [],
    )
    r = CliRunner().invoke(cli_main, ["plugins", "list"])
    assert r.exit_code == 0, r.output
    assert "example_extras" in r.output
    assert "directory" in r.output


def test_cli_plugins_describe_known(
    monkeypatch: pytest.MonkeyPatch, _clean_plugin_state: None,
    parent_of_panelforge_plugins: Path,
) -> None:
    monkeypatch.chdir(parent_of_panelforge_plugins)
    monkeypatch.setattr(
        "importlib.metadata.entry_points",
        lambda *, group="": [],
    )
    r = CliRunner().invoke(cli_main, ["plugins", "describe", "example_extras"])
    assert r.exit_code == 0, r.output
    assert "example_extras" in r.output
    assert "0.1.0" in r.output
    assert "example_extras.cohort_violin" in r.output


def test_cli_plugins_describe_unknown_exits_1(
    monkeypatch: pytest.MonkeyPatch, _clean_plugin_state: None, tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "importlib.metadata.entry_points",
        lambda *, group="": [],
    )
    r = CliRunner().invoke(cli_main, ["plugins", "describe", "nope"])
    assert r.exit_code == 1
    assert "not found" in r.output


# ─────────────────────────── catalog/index integration ──────────────────


def test_build_index_includes_plugin_field(
    monkeypatch: pytest.MonkeyPatch, _clean_plugin_state: None,
    parent_of_panelforge_plugins: Path,
) -> None:
    """`build_index()` must annotate plugin recipes with `plugin: <name>`
    and tag catalog recipes with `plugin: None`."""
    from panelforge_figures.manifest import build_index

    monkeypatch.chdir(parent_of_panelforge_plugins)
    monkeypatch.setattr(
        "importlib.metadata.entry_points",
        lambda *, group="": [],
    )
    idx = build_index(include_tags=True)

    found_plugin_recipe = False
    found_catalog_recipe = False
    for mod in idx["modalities"]:
        for rec in mod["recipes"]:
            full = f"{mod['name']}.{rec['name']}"
            assert "plugin" in rec, f"missing `plugin` field on {full}"
            if full == "example_extras.cohort_violin":
                assert rec["plugin"] == "example_extras"
                assert rec["tags_source"] == "plugin:example_extras"
                found_plugin_recipe = True
            elif rec["plugin"] is None:
                found_catalog_recipe = True

    assert found_plugin_recipe, "fixture plugin recipe missing from index"
    assert found_catalog_recipe, "no catalog recipes seen"


# ─────────────────────────── PluginInfo dataclass ───────────────────────


def test_plugin_info_is_immutable() -> None:
    """`PluginInfo` is frozen so callers can't quietly mutate cached state."""
    info = PluginInfo(name="x", version="1.0", source="directory")
    with pytest.raises(Exception):  # noqa: PT011 — dataclass FrozenInstanceError
        info.name = "y"  # type: ignore[misc]
