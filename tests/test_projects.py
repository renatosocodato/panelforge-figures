"""Tests for the cross-project orchestration registry — Sprint 3A.

Covers ``panelforge_figures.projects`` (Build-A) and
``panelforge_figures.projects.portfolio`` (Build-B) plus the new
``figures projects`` CLI surface (Build-C). Six pytest clusters mirror
``docs/spec_cross_project.md`` §10.
"""

from __future__ import annotations

import warnings
from datetime import UTC, datetime
from pathlib import Path

import pytest
from click.testing import CliRunner

from panelforge_figures.cli import main
from panelforge_figures.projects import (
    ProjectEntry,
    ProjectIdCollision,
    ProjectPathMissing,
    Registry,
    load_registry,
    register_if_absent,
    save_registry,
    switch_default,
    unregister,
    validate_registry,
)
from panelforge_figures.projects.portfolio import (
    aggregate_portfolio,
    diff_projects,
    load_project_recipe_set,
    render_heatmap_terminal,
    top_n_recipes,
)

# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


def _seed_project(
    root: Path,
    project_id: str,
    recipes: list[str],
    *,
    profile: str = "default",
) -> Path:
    """Create a synthetic project directory with a panelforge_workspace
    containing a manifest.yaml that lists ``recipes``."""
    project_dir = root / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    workspace = project_dir / "panelforge_workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    manifest = workspace / "manifest.yaml"
    panel_lines = "\n".join(
        f"  - id: panel_{i}\n    recipe: {recipe}"
        for i, recipe in enumerate(recipes)
    )
    manifest.write_text(f"panels:\n{panel_lines}\n", encoding="utf-8")
    yaml_path = project_dir / "panelforge.project.yaml"
    yaml_path.write_text(
        f"project_id: {project_id}\nactive_profile: {profile}\n",
        encoding="utf-8",
    )
    return project_dir


def _add_entry(
    registry: Registry,
    *,
    project_id: str,
    path: Path,
    recipes: int = 0,
    profile: str = "default",
    tags: tuple[str, ...] = (),
    set_default: bool = False,
) -> ProjectEntry:
    entry = ProjectEntry(
        id=project_id,
        path=path,
        last_used=datetime(2026, 5, 4, 15, 32, tzinfo=UTC),
        active_profile=profile,
        n_recipes_picked=recipes,
        last_render_status="n/a",
        tags=tags,
    )
    registry.add(entry, set_default=set_default)
    return entry


# --------------------------------------------------------------------------- #
# Cluster 1 — Round-trip                                                       #
# --------------------------------------------------------------------------- #


def test_registry_save_load_round_trip(tmp_path: Path) -> None:
    """Save then load a single-entry registry; key fields must survive."""
    cfg = tmp_path / "projects.yaml"
    proj = tmp_path / "proj_a"
    proj.mkdir()
    registry = Registry.empty()
    entry = ProjectEntry(
        id="proj_a",
        path=proj,
        last_used=datetime(2026, 5, 4, 15, 32, tzinfo=UTC),
        active_profile="disc1",
        n_recipes_picked=12,
        last_render_status="11/12 success",
        tags=("manuscript", "microglia"),
    )
    registry.add(entry, set_default=True)
    save_registry(registry, cfg)

    loaded = load_registry(cfg)
    assert loaded.default_project == "proj_a"
    assert "proj_a" in loaded.projects
    round_tripped = loaded.projects["proj_a"]
    assert round_tripped.tags == ("manuscript", "microglia")
    assert round_tripped.active_profile == "disc1"
    assert round_tripped.n_recipes_picked == 12
    assert round_tripped.last_render_status == "11/12 success"


def test_load_registry_missing_file_returns_empty(tmp_path: Path) -> None:
    """A non-existent registry file is not an error: empty Registry."""
    cfg = tmp_path / "does-not-exist.yaml"
    registry = load_registry(cfg)
    assert registry.projects == {}
    assert registry.default_project is None


# --------------------------------------------------------------------------- #
# Cluster 2 — register / switch / unregister                                   #
# --------------------------------------------------------------------------- #


def test_register_if_absent_idempotent(tmp_path: Path) -> None:
    """Two registrations of the same project must not double-add."""
    cfg = tmp_path / "projects.yaml"
    proj = tmp_path / "proj"
    proj.mkdir()
    register_if_absent(
        path=proj, project_id="proj", profile="default",
        config_path=cfg, set_default=True,
    )
    register_if_absent(
        path=proj, project_id="proj", profile="default",
        config_path=cfg, n_recipes=5, status="5/5 success",
    )
    registry = load_registry(cfg)
    assert len(registry.projects) == 1
    refreshed = registry.projects["proj"]
    assert refreshed.n_recipes_picked == 5
    assert refreshed.last_render_status == "5/5 success"


def test_register_collision_raises(tmp_path: Path) -> None:
    """Same id, different path → ProjectIdCollision."""
    cfg = tmp_path / "projects.yaml"
    proj_a = tmp_path / "a"
    proj_a.mkdir()
    proj_b = tmp_path / "b"
    proj_b.mkdir()
    register_if_absent(
        path=proj_a, project_id="shared", profile="default", config_path=cfg,
    )
    with pytest.raises(ProjectIdCollision):
        register_if_absent(
            path=proj_b, project_id="shared", profile="default", config_path=cfg,
        )


def test_switch_updates_default(tmp_path: Path) -> None:
    """``switch_default`` updates ``default_project`` on disk."""
    cfg = tmp_path / "projects.yaml"
    proj_a = tmp_path / "a"
    proj_a.mkdir()
    proj_b = tmp_path / "b"
    proj_b.mkdir()
    register_if_absent(
        path=proj_a, project_id="a", profile="default",
        config_path=cfg, set_default=True,
    )
    register_if_absent(
        path=proj_b, project_id="b", profile="default", config_path=cfg,
    )
    switch_default("b", config_path=cfg)
    registry = load_registry(cfg)
    assert registry.default_project == "b"


def test_unregister_does_not_touch_filesystem(tmp_path: Path) -> None:
    """``unregister`` removes the entry but leaves the project dir."""
    cfg = tmp_path / "projects.yaml"
    proj = tmp_path / "p"
    proj.mkdir()
    sentinel = proj / "manuscript.md"
    sentinel.write_text("alive", encoding="utf-8")
    register_if_absent(
        path=proj, project_id="p", profile="default",
        config_path=cfg, set_default=True,
    )
    unregister("p", config_path=cfg)
    registry = load_registry(cfg)
    assert "p" not in registry.projects
    # filesystem must be untouched
    assert proj.is_dir()
    assert sentinel.is_file()
    assert sentinel.read_text(encoding="utf-8") == "alive"


# --------------------------------------------------------------------------- #
# Cluster 3 — Diff                                                             #
# --------------------------------------------------------------------------- #


def test_diff_with_three_shared_emits_suggestion(tmp_path: Path) -> None:
    """3 shared + N unique recipes → suggestion is set."""
    shared = [
        "meta_and_diagnostic.bayes_factor_arrow_plot",
        "actin_microtubule_morphometry.compartment_paired_delta_scatter",
        "biophysics_scaling.equivalence_forest_with_tost_bounds",
    ]
    a_only = ["omics_differential.module_concordance_signed_heatmap"]
    b_only = [
        "factorial.sex_x_genotype_interaction_forest",
        "rhogtpase_dynamics.fret_sustain_decay",
    ]
    proj_a = _seed_project(tmp_path, "a", shared + a_only)
    proj_b = _seed_project(tmp_path, "b", shared + b_only)
    cfg = tmp_path / "projects.yaml"
    registry = Registry.empty()
    _add_entry(registry, project_id="a", path=proj_a, recipes=4, set_default=True)
    _add_entry(registry, project_id="b", path=proj_b, recipes=5)
    save_registry(registry, cfg)

    report = diff_projects(registry, "a", "b")
    assert set(report.shared) == set(shared)
    assert set(report.a_only) == set(a_only)
    assert set(report.b_only) == set(b_only)
    assert report.suggestion is not None
    assert "shared_methods" in report.suggestion


def test_diff_with_zero_shared_no_suggestion(tmp_path: Path) -> None:
    """No overlap → suggestion is None (heuristic threshold = 3)."""
    proj_a = _seed_project(tmp_path, "a", ["mod1.recipe_a"])
    proj_b = _seed_project(tmp_path, "b", ["mod2.recipe_z"])
    registry = Registry.empty()
    _add_entry(registry, project_id="a", path=proj_a, set_default=True)
    _add_entry(registry, project_id="b", path=proj_b)
    report = diff_projects(registry, "a", "b")
    assert report.shared == ()
    assert report.suggestion is None


def test_load_project_recipe_set_missing_manifest_warns(tmp_path: Path) -> None:
    """Project without a manifest yields an empty frozenset + warning."""
    proj = tmp_path / "naked"
    proj.mkdir()
    entry = ProjectEntry(
        id="naked",
        path=proj,
        last_used=datetime(2026, 5, 4, 15, 32, tzinfo=UTC),
        active_profile="default",
        n_recipes_picked=0,
        last_render_status="n/a",
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        recipes = load_project_recipe_set(entry)
    assert recipes == frozenset()
    assert any(isinstance(w.message, RuntimeWarning) for w in caught)


# --------------------------------------------------------------------------- #
# Cluster 4 — Portfolio                                                        #
# --------------------------------------------------------------------------- #


def test_portfolio_aggregation_inverts_correctly(tmp_path: Path) -> None:
    """5 mock projects; recipe→projects must invert correctly."""
    # Recipe used by all 5 (top of leaderboard)
    universal = "meta_and_diagnostic.run_provenance_card"
    # Recipe used by 3 of 5
    common = "meta_and_diagnostic.bayes_factor_arrow_plot"
    project_recipes = {
        "p1": [universal, common, "p1_only"],
        "p2": [universal, common, "p2_only_a", "p2_only_b"],
        "p3": [universal, common],
        "p4": [universal, "p4_only"],
        "p5": [universal],
    }
    registry = Registry.empty()
    for pid, recipes in project_recipes.items():
        proj = _seed_project(tmp_path, pid, recipes)
        _add_entry(
            registry, project_id=pid, path=proj,
            recipes=len(recipes),
            set_default=(pid == "p1"),
        )

    summary = aggregate_portfolio(registry)
    assert summary.n_projects == 5
    # Universal recipe maps to all 5 projects
    assert summary.recipe_to_projects[universal] == frozenset(project_recipes.keys())
    # Common maps to exactly the three using it
    assert summary.recipe_to_projects[common] == frozenset({"p1", "p2", "p3"})
    # p1_only maps to exactly p1
    assert summary.recipe_to_projects["p1_only"] == frozenset({"p1"})

    top = top_n_recipes(summary, n=10)
    # Top entry must be the universal recipe (5/5)
    assert top[0].recipe_full_name == universal
    assert top[0].project_count == 5
    # Second must be common (3/5)
    assert top[1].recipe_full_name == common
    assert top[1].project_count == 3


def test_render_heatmap_terminal_dimensions(tmp_path: Path) -> None:
    """Terminal heatmap output has one header line per recipe."""
    project_recipes = {
        "alpha": ["m.r1", "m.r2"],
        "beta": ["m.r1", "m.r3"],
    }
    registry = Registry.empty()
    for pid, recipes in project_recipes.items():
        proj = _seed_project(tmp_path, pid, recipes)
        _add_entry(registry, project_id=pid, path=proj,
                   recipes=len(recipes), set_default=(pid == "alpha"))
    summary = aggregate_portfolio(registry)
    out = render_heatmap_terminal(summary)
    # Should contain each recipe id at least once
    for recipe in ("m.r1", "m.r2", "m.r3"):
        assert recipe in out
    # Two project columns
    assert "alpha" in out
    assert "beta" in out
    # Bullet rendered
    assert "•" in out


def test_render_heatmap_terminal_empty_portfolio(tmp_path: Path) -> None:
    """No projects → output mentions 0 / 0 without raising."""
    summary = aggregate_portfolio(Registry.empty())
    out = render_heatmap_terminal(summary)
    assert "0 projects" in out


# --------------------------------------------------------------------------- #
# Cluster 5 — Validate / missing path                                          #
# --------------------------------------------------------------------------- #


def test_validate_drops_missing_paths(tmp_path: Path) -> None:
    """``validate_registry`` removes entries whose path no longer exists."""
    cfg = tmp_path / "projects.yaml"
    proj = tmp_path / "live"
    proj.mkdir()
    register_if_absent(
        path=proj, project_id="live", profile="default",
        config_path=cfg, set_default=True,
    )
    # Inject a stale entry by direct manipulation.
    registry = load_registry(cfg)
    stale_path = tmp_path / "ghost"
    registry.projects["ghost"] = ProjectEntry(
        id="ghost",
        path=stale_path,
        last_used=datetime(2026, 5, 4, 15, 32, tzinfo=UTC),
        active_profile="default",
        n_recipes_picked=0,
        last_render_status="n/a",
    )
    save_registry(registry, cfg)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        dropped = validate_registry(prompt=False, config_path=cfg)
    assert "ghost" in dropped
    on_disk = load_registry(cfg)
    assert "ghost" not in on_disk.projects
    assert "live" in on_disk.projects


def test_switch_to_missing_path_raises(tmp_path: Path) -> None:
    """Switching to a project whose path is gone raises ProjectPathMissing."""
    cfg = tmp_path / "projects.yaml"
    proj = tmp_path / "p"
    proj.mkdir()
    register_if_absent(
        path=proj, project_id="p", profile="default",
        config_path=cfg, set_default=True,
    )
    # Drop the project directory after registration.
    sentinel = proj / "x"
    sentinel.write_text("y", encoding="utf-8")
    sentinel.unlink()
    proj.rmdir()
    with pytest.raises(ProjectPathMissing):
        switch_default("p", config_path=cfg)


# --------------------------------------------------------------------------- #
# Cluster 6 — Corrupted YAML                                                   #
# --------------------------------------------------------------------------- #


def test_corrupted_yaml_returns_empty_with_warning(tmp_path: Path) -> None:
    """Malformed YAML must fall back to empty Registry + warning + backup."""
    cfg = tmp_path / "projects.yaml"
    cfg.write_text(
        "schema_version: 1\nprojects: this is broken yaml: [[",
        encoding="utf-8",
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        registry = load_registry(cfg)
    assert registry.projects == {}
    assert any(
        ("broken" in str(w.message).lower() or "corrupt" in str(w.message).lower())
        for w in caught
    )
    # The .broken-<ts> backup must exist
    assert any(
        p.name.startswith("projects.yaml.broken-") for p in tmp_path.iterdir()
    )


# --------------------------------------------------------------------------- #
# CLI smoke tests                                                              #
# --------------------------------------------------------------------------- #


def test_cli_projects_list_empty_registry(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["projects", "list", "--config-path", str(tmp_path / "projects.yaml")],
    )
    assert result.exit_code == 0
    assert "no projects" in result.output.lower()


def test_cli_projects_register_then_list(tmp_path: Path) -> None:
    runner = CliRunner()
    proj_dir = tmp_path / "proj"
    proj_dir.mkdir()
    (proj_dir / "panelforge.project.yaml").write_text(
        "project_id: my_proj\n", encoding="utf-8"
    )
    cfg = tmp_path / "projects.yaml"
    result = runner.invoke(
        main, ["projects", "register", str(proj_dir), "--config-path", str(cfg)]
    )
    assert result.exit_code == 0, result.output
    assert "my_proj" in result.output
    listing = runner.invoke(
        main, ["projects", "list", "--config-path", str(cfg)]
    )
    assert listing.exit_code == 0
    assert "my_proj" in listing.output


def test_cli_projects_current_no_default_exits_1(tmp_path: Path) -> None:
    runner = CliRunner()
    cfg = tmp_path / "projects.yaml"
    result = runner.invoke(main, ["projects", "current", "--config-path", str(cfg)])
    assert result.exit_code == 1


def test_cli_projects_current_prints_active(tmp_path: Path) -> None:
    runner = CliRunner()
    proj_dir = tmp_path / "p"
    proj_dir.mkdir()
    cfg = tmp_path / "projects.yaml"
    runner.invoke(
        main, ["projects", "register", str(proj_dir), "--id", "p", "--config-path", str(cfg)]
    )
    result = runner.invoke(main, ["projects", "current", "--config-path", str(cfg)])
    assert result.exit_code == 0
    assert "Active project" in result.output
    assert "p" in result.output


def test_cli_projects_switch_unknown_id_exits_1(tmp_path: Path) -> None:
    runner = CliRunner()
    cfg = tmp_path / "projects.yaml"
    result = runner.invoke(
        main, ["projects", "switch", "ghost", "--config-path", str(cfg)]
    )
    assert result.exit_code == 1


def test_cli_projects_unregister_round_trip(tmp_path: Path) -> None:
    runner = CliRunner()
    proj_dir = tmp_path / "p"
    proj_dir.mkdir()
    cfg = tmp_path / "projects.yaml"
    runner.invoke(
        main, ["projects", "register", str(proj_dir), "--id", "p", "--config-path", str(cfg)]
    )
    result = runner.invoke(
        main, ["projects", "unregister", "p", "--config-path", str(cfg)]
    )
    assert result.exit_code == 0
    listing = runner.invoke(main, ["projects", "list", "--config-path", str(cfg)])
    assert "p" not in listing.output.split("\n")[1:]  # not in body, only header


def test_cli_projects_validate_yes_drops_stale(tmp_path: Path) -> None:
    runner = CliRunner()
    cfg = tmp_path / "projects.yaml"
    proj = tmp_path / "live"
    proj.mkdir()
    register_if_absent(
        path=proj, project_id="live", profile="default",
        config_path=cfg, set_default=True,
    )
    # Inject a stale entry pointing to a non-existent path.
    registry = load_registry(cfg)
    registry.projects["ghost"] = ProjectEntry(
        id="ghost",
        path=tmp_path / "ghost",
        last_used=datetime(2026, 5, 4, 15, 32, tzinfo=UTC),
        active_profile="default",
        n_recipes_picked=0,
        last_render_status="n/a",
    )
    save_registry(registry, cfg)
    # validate_registry emits a RuntimeWarning per dropped entry when stdin
    # is not a TTY (which it never is under CliRunner). pyproject's
    # ``filterwarnings = ["error"]`` would otherwise turn that into an
    # exception inside the Click invocation.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        result = runner.invoke(
            main,
            ["projects", "validate", "--yes", "--config-path", str(cfg)],
        )
    assert result.exit_code == 0, result.output
    assert "Dropped" in result.output


def test_cli_projects_diff_shows_overlap(tmp_path: Path) -> None:
    runner = CliRunner()
    cfg = tmp_path / "projects.yaml"
    shared = [
        "meta_and_diagnostic.bayes_factor_arrow_plot",
        "actin_microtubule_morphometry.compartment_paired_delta_scatter",
        "biophysics_scaling.equivalence_forest_with_tost_bounds",
    ]
    proj_a = _seed_project(tmp_path, "a", shared + ["mod.a_only"])
    proj_b = _seed_project(tmp_path, "b", shared + ["mod.b_only"])
    register_if_absent(
        path=proj_a, project_id="a", profile="default",
        config_path=cfg, set_default=True,
    )
    register_if_absent(
        path=proj_b, project_id="b", profile="default", config_path=cfg,
    )
    result = runner.invoke(
        main, ["projects", "diff", "a", "b", "--config-path", str(cfg)]
    )
    assert result.exit_code == 0
    assert "Shared (3)" in result.output
    assert "shared_methods" in result.output


def test_cli_projects_portfolio_summary(tmp_path: Path) -> None:
    runner = CliRunner()
    cfg = tmp_path / "projects.yaml"
    for pid, recipes in {
        "alpha": ["mod.r1", "mod.r2"],
        "beta": ["mod.r1", "mod.r3"],
    }.items():
        proj = _seed_project(tmp_path, pid, recipes)
        register_if_absent(
            path=proj, project_id=pid, profile="default",
            config_path=cfg, set_default=(pid == "alpha"),
        )
    result = runner.invoke(
        main, ["projects", "portfolio", "--config-path", str(cfg)]
    )
    assert result.exit_code == 0
    assert "Portfolio summary" in result.output
    assert "Top 10 recipes" in result.output


# --------------------------------------------------------------------------- #
# Auto-register hook (project_scan.py)                                         #
# --------------------------------------------------------------------------- #


def test_scan_project_auto_registers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``scan_project`` calls register_if_absent silently on first scan."""
    from panelforge_figures.manifest.project_scan import scan_project

    xdg = tmp_path / "xdg"
    xdg.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "panelforge.project.yaml").write_text(
        "project_id: scanned_proj\nactive_profile: disc1\n",
        encoding="utf-8",
    )
    scan_project(proj, available_modalities=("meta_and_diagnostic",))
    cfg = xdg / "panelforge" / "projects.yaml"
    assert cfg.is_file()
    registry = load_registry(cfg)
    assert "scanned_proj" in registry.projects


def test_scan_project_auto_register_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``auto_register=False`` suppresses the side effect."""
    from panelforge_figures.manifest.project_scan import scan_project

    xdg = tmp_path / "xdg"
    xdg.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "panelforge.project.yaml").write_text(
        "project_id: skipped\nactive_profile: disc1\n",
        encoding="utf-8",
    )
    scan_project(
        proj,
        available_modalities=("meta_and_diagnostic",),
        auto_register=False,
    )
    cfg = xdg / "panelforge" / "projects.yaml"
    assert not cfg.exists()


def test_scan_project_yaml_opt_out(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``auto_register: false`` in panelforge.project.yaml is sticky."""
    from panelforge_figures.manifest.project_scan import scan_project

    xdg = tmp_path / "xdg"
    xdg.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "panelforge.project.yaml").write_text(
        "project_id: opted_out\nauto_register: false\n",
        encoding="utf-8",
    )
    scan_project(proj, available_modalities=("meta_and_diagnostic",))
    cfg = xdg / "panelforge" / "projects.yaml"
    assert not cfg.exists()
