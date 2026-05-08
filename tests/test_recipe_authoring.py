"""Tests for the recipe authoring co-pilot (Elevation 6).

Covers:

* Name validators (modality + recipe) — accept lowercase_snake_case,
  reject everything else.
* ``list_supported_families`` enumerates the five family templates.
* ``scaffold_recipe`` returns a fully populated :class:`RecipeScaffold`
  with target paths under ``project_root`` and source text containing
  the family + research question + ``register_recipe`` decorator.
* ``scaffold_recipe`` raises on an unsupported family.
* The generated test module references ``test_smoke``.
* ``write_scaffold`` materialises both files (and creates the gallery
  directory) and refuses to overwrite by default.
* The generated recipe and test parse as valid Python via :mod:`ast`.
* CLI: ``figures author-recipe --help`` succeeds and the command
  produces real files when invoked against a temp project root.
"""

from __future__ import annotations

import ast
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from panelforge_figures.cli import main as cli_main
from panelforge_figures.manifest.recipe_authoring import (
    FAMILY_TEMPLATES,
    RecipeAuthoringError,
    RecipeScaffold,
    list_supported_families,
    scaffold_demo_data_generator,
    scaffold_recipe,
    scaffold_recipe_test,
    validate_modality_name,
    validate_recipe_name,
    write_scaffold,
)

# ─────────────────────────── name validators ─────────────────────────────


@pytest.mark.parametrize(
    "good",
    ["actin_morphometry", "rhogtpase_dynamics", "x", "ab12_c", "a1"],
)
def test_validate_modality_name_accepts_snake_case(good: str) -> None:
    validate_modality_name(good)  # must not raise


@pytest.mark.parametrize("bad", ["Actin", "", "1foo", "with space", "Foo_Bar", "-bad"])
def test_validate_modality_name_rejects_invalid(bad: str) -> None:
    with pytest.raises(RecipeAuthoringError):
        validate_modality_name(bad)


@pytest.mark.parametrize(
    "good",
    ["two_way_anova_summary_plot", "term_forest", "x"],
)
def test_validate_recipe_name_accepts_snake_case(good: str) -> None:
    validate_recipe_name(good)


@pytest.mark.parametrize("bad", ["MixedCase", "", "1leading_digit", "with-dash"])
def test_validate_recipe_name_rejects_invalid(bad: str) -> None:
    with pytest.raises(RecipeAuthoringError):
        validate_recipe_name(bad)


# ─────────────────────────── family registry ─────────────────────────────


def test_list_supported_families_exposes_five() -> None:
    """The Elevation 6 spec promises exactly the five family templates."""
    families = list_supported_families()
    assert set(families) == {
        "coef_forest",
        "comparison",
        "correlation",
        "factorial",
        "equivalence",
    }
    # No accidental duplicates and FAMILY_TEMPLATES is the source of truth.
    assert tuple(FAMILY_TEMPLATES.keys()) == families


def test_demo_generators_exist_for_every_family() -> None:
    for f in list_supported_families():
        body = scaffold_demo_data_generator(f)
        assert "_DemoInput" in body
        assert "return" in body


def test_demo_generator_unknown_family_raises() -> None:
    with pytest.raises(RecipeAuthoringError):
        scaffold_demo_data_generator("not_a_family")


# ─────────────────────────── scaffold_recipe ──────────────────────────────


def _make_scaffold(tmp_path: Path, **overrides) -> RecipeScaffold:
    kwargs = dict(
        modality="custom_lab",
        recipe_name="my_forest_demo",
        family="coef_forest",
        research_question=(
            "Across three terms, which has the largest standardised effect "
            "on the response, and is its 95% CI bounded away from zero?"
        ),
        project_root=tmp_path,
    )
    kwargs.update(overrides)
    return scaffold_recipe(**kwargs)


def test_scaffold_recipe_returns_populated_scaffold(tmp_path: Path) -> None:
    s = _make_scaffold(tmp_path)
    assert isinstance(s, RecipeScaffold)
    assert s.modality == "custom_lab"
    assert s.recipe_name == "my_forest_demo"
    assert s.family == "coef_forest"
    expected_recipe_path = (
        tmp_path / "src" / "panelforge_figures" / "recipes"
        / "custom_lab" / "my_forest_demo.py"
    )
    expected_test_path = tmp_path / "tests" / "recipes" / "test_my_forest_demo.py"
    expected_gallery = (
        tmp_path / "docs" / "gallery" / "custom_lab" / "my_forest_demo.png"
    )
    assert s.recipe_module_path == expected_recipe_path
    assert s.test_module_path == expected_test_path
    assert s.gallery_png_path == expected_gallery
    assert s.statistical_contract_dict["min_n_per_group"] == 10
    # Family overrides flow through.
    s2 = _make_scaffold(tmp_path, family="correlation")
    assert s2.statistical_contract_dict["min_n_per_group"] == 30


def test_scaffold_recipe_rejects_unknown_family(tmp_path: Path) -> None:
    with pytest.raises(RecipeAuthoringError):
        _make_scaffold(tmp_path, family="not_a_family")


def test_scaffold_recipe_rejects_invalid_modality(tmp_path: Path) -> None:
    with pytest.raises(RecipeAuthoringError):
        _make_scaffold(tmp_path, modality="Bad-Modality")


def test_scaffold_recipe_rejects_empty_research_question(tmp_path: Path) -> None:
    with pytest.raises(RecipeAuthoringError):
        _make_scaffold(tmp_path, research_question="   ")


def test_recipe_module_text_has_required_pieces(tmp_path: Path) -> None:
    """Smoke-test the generated recipe module contains the load-bearing
    structural elements: registration call, family enum, research
    question, and a ``render`` symbol."""
    s = _make_scaffold(tmp_path)
    src = s.recipe_module_text
    assert "register_recipe" in src
    assert "RecipeFamily.coef_forest" in src
    assert s.research_question in src
    assert "def render(" in src
    # The class name follows CamelCase(recipe_name) + "Input" — verify both
    # the contract class and the alias are present.
    assert "class MyForestDemoInput(RecipeContract)" in src
    assert "_DemoInput = MyForestDemoInput" in src


def test_test_module_text_has_smoke_test(tmp_path: Path) -> None:
    s = _make_scaffold(tmp_path)
    assert "test_smoke" in s.test_module_text
    assert "test_metadata_family" in s.test_module_text
    # Standalone helper for callers that only want the test text.
    direct = scaffold_recipe_test(
        modality="custom_lab", recipe_name="my_forest_demo", family="coef_forest",
    )
    assert direct == s.test_module_text


@pytest.mark.parametrize("family", sorted(FAMILY_TEMPLATES.keys()))
def test_scaffolded_modules_parse_as_python(family: str, tmp_path: Path) -> None:
    """Every family must produce ast-parseable recipe + test source."""
    s = _make_scaffold(
        tmp_path,
        family=family,
        recipe_name=f"{family}_demo_recipe",
    )
    ast.parse(s.recipe_module_text)
    ast.parse(s.test_module_text)


# ─────────────────────────── write_scaffold ───────────────────────────────


def test_write_scaffold_writes_recipe_and_test(tmp_path: Path) -> None:
    s = _make_scaffold(tmp_path)
    paths = write_scaffold(s)
    assert paths["recipe"].exists()
    assert paths["test"].exists()
    assert paths["recipe"].read_text() == s.recipe_module_text
    assert paths["test"].read_text() == s.test_module_text
    # Gallery directory is created even if the PNG is rendered later.
    assert s.gallery_png_path.parent.exists()


def test_write_scaffold_refuses_to_overwrite_by_default(tmp_path: Path) -> None:
    s = _make_scaffold(tmp_path)
    write_scaffold(s)
    with pytest.raises(RecipeAuthoringError):
        write_scaffold(s)
    # overwrite=True succeeds.
    write_scaffold(s, overwrite=True)


def test_write_scaffold_creates_parent_directories(tmp_path: Path) -> None:
    s = _make_scaffold(tmp_path)
    # parent dirs do not exist yet — write_scaffold must create them
    assert not s.recipe_module_path.parent.exists()
    write_scaffold(s)
    assert s.recipe_module_path.parent.exists()
    assert s.test_module_path.parent.exists()


# ─────────────────────────── CLI smoke ────────────────────────────────────


def test_cli_author_recipe_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli_main, ["author-recipe", "--help"])
    assert result.exit_code == 0, result.output
    assert "author-recipe" in result.output
    assert "--family" in result.output
    assert "coef_forest" in result.output


def test_cli_author_recipe_writes_files(tmp_path: Path) -> None:
    """End-to-end: invoke the CLI with --no-render-demo (avoids matplotlib
    on the import path) and assert the recipe + test files exist on disk
    and are valid Python."""
    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        [
            "author-recipe",
            "--modality", "custom_lab",
            "--name", "term_significance_forest",
            "--family", "coef_forest",
            "--research-question",
            "Which terms have CIs that exclude zero?",
            "--project-root", str(tmp_path),
            "--no-render-demo",
        ],
    )
    assert result.exit_code == 0, result.output
    recipe_path = (
        tmp_path / "src" / "panelforge_figures" / "recipes" / "custom_lab"
        / "term_significance_forest.py"
    )
    test_path = (
        tmp_path / "tests" / "recipes" / "test_term_significance_forest.py"
    )
    assert recipe_path.exists()
    assert test_path.exists()
    ast.parse(recipe_path.read_text())
    ast.parse(test_path.read_text())


def test_cli_author_recipe_invalid_family(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        [
            "author-recipe",
            "--modality", "custom_lab",
            "--name", "bad",
            "--family", "definitely_not_a_family",
            "--research-question", "anything",
            "--project-root", str(tmp_path),
            "--no-render-demo",
        ],
    )
    # Click's choice validation triggers a usage error with a non-zero exit.
    assert result.exit_code != 0


def test_cli_author_recipe_invalid_modality(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        [
            "author-recipe",
            "--modality", "Bad-Modality",
            "--name", "name",
            "--family", "coef_forest",
            "--research-question", "q",
            "--project-root", str(tmp_path),
            "--no-render-demo",
        ],
    )
    assert result.exit_code != 0
    assert "lowercase_snake_case" in (result.output + (result.stderr or ""))


# ─────────────────────────── render demo (optional) ───────────────────────


def test_render_demo_to_gallery_produces_png(tmp_path: Path) -> None:
    """Spin up an isolated package layout, write the scaffold + a stub
    modality ``__init__`` so the recipe module can be imported, and let
    ``render_demo_to_gallery`` produce the demo PNG.

    Uses ``e6smoke`` (valid lowercase_snake_case) as the temporary
    modality name so the validators don't reject it.
    """
    pytest.importorskip("matplotlib")
    src_pkg = (
        Path(__file__).resolve().parent.parent
        / "src" / "panelforge_figures" / "recipes"
    )
    modality = "e6smoke"
    target_modality_dir = src_pkg / modality
    target_modality_dir.mkdir(parents=True, exist_ok=True)
    (target_modality_dir / "__init__.py").write_text(
        "from ...core.contract import register_modality\n"
        f"register_modality(name='{modality}', description='E6 smoke')\n"
    )
    s: RecipeScaffold | None = None
    try:
        s = scaffold_recipe(
            modality=modality,
            recipe_name="forest_smoke_e6",
            family="coef_forest",
            research_question="smoke",
            project_root=Path(__file__).resolve().parent.parent,
        )
        write_scaffold(s, overwrite=True)
        from panelforge_figures.manifest.recipe_authoring import (
            render_demo_to_gallery,
        )

        out = render_demo_to_gallery(s)
        assert out.exists()
        assert out.suffix == ".png"
        assert out.stat().st_size > 0
    finally:
        if target_modality_dir.exists():
            shutil.rmtree(target_modality_dir, ignore_errors=True)
        if s is not None:
            if s.gallery_png_path.exists():
                s.gallery_png_path.unlink()
            for p in (s.recipe_module_path, s.test_module_path):
                if p.exists():
                    p.unlink()
        stale = [
            name for name in list(sys.modules)
            if name.startswith(f"panelforge_figures.recipes.{modality}")
        ]
        for name in stale:
            sys.modules.pop(name, None)


# ─────────────────────────── version sanity ───────────────────────────────


def test_version_is_at_least_v3() -> None:
    """E6 (recipe authoring) ships starting in v3.0.0rc1; subsequent
    elevations may bump higher."""
    from panelforge_figures import __version__

    parts = __version__.split(".")
    assert int(parts[0]) >= 3, f"expected >= 3.x.y, got {__version__!r}"


# ─────────────────────────── module import isolation ─────────────────────


def test_subprocess_cli_help() -> None:
    """Belt-and-braces: invoke the CLI as a subprocess to confirm the new
    command is wired into the published entry point."""
    result = subprocess.run(
        [sys.executable, "-m", "panelforge_figures.cli", "author-recipe", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (result.stdout + result.stderr)
    assert "author-recipe" in result.stdout
