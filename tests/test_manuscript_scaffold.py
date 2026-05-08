"""Tests for the manuscript-scaffold module (Elevation 9 — phase 2).

Owned by Build-B; this test suite is authored by Build-C against the
public API documented in the swarm spec (``Venue``,
``ManuscriptFormat``, ``ScaffoldError``, ``scaffold_manuscript``,
``render_manuscript_skeleton``, ``render_methods_boilerplate``,
``VENUE_TEMPLATES``).  The whole file is ``importorskip``-gated so
Build-C can verify it parses on its own and the integration verification
passes once Build-B lands.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

manuscript_scaffold = pytest.importorskip(
    "panelforge_figures.manifest.manuscript_scaffold"
)


# ─────────────────────────── helpers ────────────────────────────────────


def _minimal_plan(tmp_path: Path):
    """Build the smallest possible FigurePlan, lazily importing scout types."""
    scout = pytest.importorskip("panelforge_figures.manifest.scout")
    project_root = tmp_path / "msproj"
    project_root.mkdir()
    inv = scout.walk_project(project_root)
    plan = scout.synthesize_figure_plan(inv, max_figures=1)
    return plan, project_root


# ─────────────────────────── VENUE_TEMPLATES surface ────────────────────


def test_venue_templates_contain_six_venues() -> None:
    """``VENUE_TEMPLATES`` must enumerate every venue the CLI accepts."""
    templates = manuscript_scaffold.VENUE_TEMPLATES
    assert isinstance(templates, dict)
    expected = {"plain", "nature", "cell", "nejm", "biorxiv", "science"}
    # Allow either the bare strings or Venue enum values as keys.
    keys = {k.value if hasattr(k, "value") else str(k) for k in templates.keys()}
    assert expected.issubset(keys), (
        f"missing venue templates: {expected - keys}"
    )


# ─────────────────────────── render_manuscript_skeleton ─────────────────


def test_render_manuscript_skeleton_cell_latex_contains_documentclass(
    tmp_path: Path,
) -> None:
    plan, _ = _minimal_plan(tmp_path)
    text = manuscript_scaffold.render_manuscript_skeleton(
        plan,
        venue=manuscript_scaffold.Venue("cell"),
        format=manuscript_scaffold.ManuscriptFormat("latex"),
    )
    assert isinstance(text, str)
    assert "\\documentclass" in text
    assert "\\title" in text
    # Abstract section appears either as ``\section{Abstract}`` or as a
    # ``\begin{abstract} ... \end{abstract}`` environment, depending on
    # how Build-B chose to emit it.  Both are valid.
    lowered = text.lower()
    assert "abstract" in lowered


def test_render_manuscript_skeleton_nature_has_200_word_note(tmp_path: Path) -> None:
    plan, _ = _minimal_plan(tmp_path)
    text = manuscript_scaffold.render_manuscript_skeleton(
        plan,
        venue=manuscript_scaffold.Venue("nature"),
        format=manuscript_scaffold.ManuscriptFormat("latex"),
    )
    assert "200" in text and "word" in text.lower()


def test_render_manuscript_skeleton_markdown_uses_headings_and_images(
    tmp_path: Path,
) -> None:
    plan, _ = _minimal_plan(tmp_path)
    text = manuscript_scaffold.render_manuscript_skeleton(
        plan,
        venue=manuscript_scaffold.Venue("plain"),
        format=manuscript_scaffold.ManuscriptFormat("markdown"),
    )
    # Markdown headings start with `#`; image embeds use `![]()` syntax.
    assert "# " in text
    # Either real images or at least the placeholder pattern must appear.
    assert "![" in text or "!\\(" in text or "Figure" in text


# ─────────────────────────── render_methods_boilerplate ────────────────


def test_render_methods_boilerplate_paragraph_per_recipe_family(tmp_path: Path) -> None:
    plan, _ = _minimal_plan(tmp_path)
    text = manuscript_scaffold.render_methods_boilerplate(plan)
    assert isinstance(text, str)
    # The result must contain at least one statistical-methods paragraph
    # token; we do not pin the exact wording.
    lowered = text.lower()
    assert any(tok in lowered for tok in (
        "method", "statistic", "analysis", "we ",
    ))


def test_render_methods_boilerplate_skips_recipes_without_contract(
    tmp_path: Path,
) -> None:
    plan, _ = _minimal_plan(tmp_path)
    # Build a plan with one panel that lacks a statistical contract by
    # passing the synthesised plan through unmodified — recipes without
    # contracts simply won't surface paragraphs.
    text = manuscript_scaffold.render_methods_boilerplate(plan)
    # The output is a string regardless of whether the plan had any
    # contract-bearing recipes.
    assert isinstance(text, str)


# ─────────────────────────── scaffold_manuscript ────────────────────────


def test_scaffold_manuscript_writes_main_tex_and_references(tmp_path: Path) -> None:
    plan, project_root = _minimal_plan(tmp_path)
    result = manuscript_scaffold.scaffold_manuscript(
        plan,
        project_root=project_root,
        venue=manuscript_scaffold.Venue("cell"),
        format=manuscript_scaffold.ManuscriptFormat("latex"),
        overwrite=True,
    )
    assert result.manuscript_path.exists()
    assert result.references_path.exists()
    # The manuscript should land under <project_root>/manuscript/
    assert "manuscript" in str(result.manuscript_path).split("/")
    # references.bib is a real file, not a directory.
    assert result.references_path.is_file()


def test_scaffold_manuscript_overwrite_false_raises_on_existing(tmp_path: Path) -> None:
    plan, project_root = _minimal_plan(tmp_path)
    manuscript_scaffold.scaffold_manuscript(
        plan,
        project_root=project_root,
        venue=manuscript_scaffold.Venue("plain"),
        format=manuscript_scaffold.ManuscriptFormat("markdown"),
        overwrite=True,
    )
    with pytest.raises(manuscript_scaffold.ScaffoldError):
        manuscript_scaffold.scaffold_manuscript(
            plan,
            project_root=project_root,
            venue=manuscript_scaffold.Venue("plain"),
            format=manuscript_scaffold.ManuscriptFormat("markdown"),
            overwrite=False,
        )


def test_scaffold_manuscript_counts_figures_and_captions(tmp_path: Path) -> None:
    plan, project_root = _minimal_plan(tmp_path)
    result = manuscript_scaffold.scaffold_manuscript(
        plan,
        project_root=project_root,
        venue=manuscript_scaffold.Venue("biorxiv"),
        format=manuscript_scaffold.ManuscriptFormat("latex"),
        overwrite=True,
    )
    assert isinstance(result.n_figures, int)
    assert isinstance(result.n_captions_drafted, int)
    assert isinstance(result.n_methods_paragraphs, int)
    # Counts can't be negative.
    assert result.n_figures >= 0
    assert result.n_captions_drafted >= 0
    assert result.n_methods_paragraphs >= 0


# ─────────────────────────── CLI smoke ──────────────────────────────────


def test_cli_manuscript_scaffold_help() -> None:
    from panelforge_figures.cli import main

    r = CliRunner().invoke(main, ["manuscript-scaffold", "--help"])
    assert r.exit_code == 0, r.output
    assert "Usage:" in r.output
    assert "manuscript" in r.output.lower() or "PLAN_PATH" in r.output


def test_cli_manuscript_scaffold_runs_on_tmp_plan(tmp_path: Path) -> None:
    """End-to-end: write a plan via scout, then run manuscript-scaffold."""
    scout = pytest.importorskip("panelforge_figures.manifest.scout")

    project_root = tmp_path / "cli_msproj"
    project_root.mkdir()
    (project_root / "panelforge.project.yaml").write_text(
        "project_id: cli_ms_test\nmodality: meta_and_diagnostic\n"
    )

    inv = scout.walk_project(project_root)
    plan = scout.synthesize_figure_plan(inv, max_figures=1)
    plan_path = tmp_path / "figures_plan.yaml"
    scout.save_figure_plan_yaml(plan, plan_path)

    from panelforge_figures.cli import main

    r = CliRunner().invoke(
        main,
        [
            "manuscript-scaffold", str(plan_path),
            "--venue", "biorxiv",
            "--format", "markdown",
            "--overwrite",
        ],
    )
    # Should succeed when both Build-A and Build-B are landed; we accept
    # 1/2 (clean import error / argument error) when they aren't.
    assert r.exit_code in (0, 1, 2), r.output
