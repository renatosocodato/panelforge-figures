"""Tests for ``manifest.star_methods`` — Elevation 12 (v3.6.0).

Covers:

* The public API surface (``KeyResource``, ``ResourceCategory``,
  ``StarMethodsTable``, ``StarMethodsError``, ``STAR_METHODS_TEMPLATE``).
* ``extract_key_resources`` software / deposited-data / reagent harvest.
* ``render_star_methods_table_latex`` / ``...markdown`` formatting.
* ``render_method_details_section`` / ``render_quantification_section``
  with stub ``FigurePlan``-like objects.
* ``generate_star_methods`` end-to-end.
* CLI smoke for ``figures star-methods``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest
from click.testing import CliRunner

from panelforge_figures.cli import main as cli_main
from panelforge_figures.manifest.star_methods import (
    STAR_METHODS_TEMPLATE,
    KeyResource,
    ResourceCategory,
    StarMethodsError,
    StarMethodsTable,
    extract_key_resources,
    generate_star_methods,
    render_method_details_section,
    render_quantification_section,
    render_star_methods_table_latex,
    render_star_methods_table_markdown,
)

# ─────────────────────── stubs (mimic FigurePlan duck-types) ───────────────────


@dataclass(frozen=True)
class _StubPanel:
    recipe_full_name: str


@dataclass(frozen=True)
class _StubFigure:
    figure_id: str
    panels: tuple[_StubPanel, ...]


@dataclass(frozen=True)
class _StubPlan:
    figures: tuple[_StubFigure, ...]


# ─────────────────────────── 1. STAR_METHODS_TEMPLATE surface ──────────────────


def test_template_has_required_keys() -> None:
    assert "sections_order" in STAR_METHODS_TEMPLATE
    assert "venues_supported" in STAR_METHODS_TEMPLATE
    assert "default_venue" in STAR_METHODS_TEMPLATE
    assert STAR_METHODS_TEMPLATE["default_venue"] == "cell"
    assert "cell" in STAR_METHODS_TEMPLATE["venues_supported"]


def test_resource_category_enum_has_nine_main_categories() -> None:
    """Cell STAR Methods spec lists nine canonical categories (plus ``other``)."""
    members = {c.value for c in ResourceCategory}
    expected_subset = {
        "Antibodies",
        "Chemicals, Peptides, and Recombinant Proteins",
        "Critical Commercial Assays",
        "Deposited Data",
        "Experimental Models: Cell Lines",
        "Experimental Models: Organisms/Strains",
        "Oligonucleotides",
        "Recombinant DNA",
        "Software and Algorithms",
    }
    assert expected_subset.issubset(members)


# ─────────────────────────── 2. extract_key_resources ─────────────────────────


def test_extract_key_resources_empty_project(tmp_path: Path) -> None:
    """Brand-new empty directory yields zero resources, doesn't raise."""
    rows = extract_key_resources(tmp_path)
    assert isinstance(rows, tuple)
    # No pyproject.toml, no provenance, no panelforge.project.yaml.
    assert rows == ()


def test_extract_key_resources_software_from_pyproject(tmp_path: Path) -> None:
    """``pyproject.toml`` dependencies become Software rows."""
    (tmp_path / "pyproject.toml").write_text(
        """\
[project]
name = "myproj"
version = "0.1.0"
dependencies = [
    "numpy>=1.24",
    "pandas==2.0",
    "click",
]
""",
        encoding="utf-8",
    )
    rows = extract_key_resources(tmp_path)
    sw = [r for r in rows if r.category == ResourceCategory.software_algorithms]
    names = {r.reagent_or_resource for r in sw}
    assert {"numpy", "pandas", "click", "myproj"}.issubset(names)
    # Version pin embedded in identifier for numpy.
    numpy_row = next(r for r in sw if r.reagent_or_resource == "numpy")
    assert ">=1.24" in numpy_row.identifier


def test_extract_key_resources_deposited_data_from_provenance(tmp_path: Path) -> None:
    """Provenance sidecars contribute Deposited Data rows."""
    workspace = tmp_path / "panelforge_workspace" / "figures"
    workspace.mkdir(parents=True)
    sidecar = workspace / "figure_1.pdf.provenance.json"
    sidecar.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "figure_path": "figure_1.pdf",
                "figure_sha256": "a" * 64,
                "rendered_at": "2026-01-01T00:00:00Z",
                "recipe": {},
                "data": {
                    "sources": [
                        {
                            "path": "data/raw.csv",
                            "sha256": "b" * 64,
                            "format": "csv",
                            "n_rows": 100,
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    rows = extract_key_resources(tmp_path)
    deposited = [r for r in rows if r.category == ResourceCategory.deposited_data]
    assert len(deposited) == 1
    assert "raw.csv" in deposited[0].reagent_or_resource
    assert deposited[0].identifier.startswith("sha256:")


def test_extract_key_resources_reagents_from_yaml(tmp_path: Path) -> None:
    """``panelforge.project.yaml`` reagent blocks become resource rows."""
    pytest.importorskip("yaml")
    (tmp_path / "panelforge.project.yaml").write_text(
        """\
antibodies:
  - name: "anti-CD11b"
    source: "Abcam"
    identifier: "ab133357"
organisms:
  - name: "C57BL/6J"
    source: "Jackson Laboratory"
    identifier: "RRID:IMSR_JAX:000664"
""",
        encoding="utf-8",
    )
    rows = extract_key_resources(tmp_path)
    abs_rows = [r for r in rows if r.category == ResourceCategory.antibodies]
    orgs = [r for r in rows if r.category == ResourceCategory.organisms]
    assert any("CD11b" in r.reagent_or_resource for r in abs_rows)
    assert any("C57BL/6J" in r.reagent_or_resource for r in orgs)


def test_extract_key_resources_sort_is_deterministic(tmp_path: Path) -> None:
    """Re-running on the same project yields byte-identical row order."""
    (tmp_path / "pyproject.toml").write_text(
        """\
[project]
name = "p"
version = "0.0.1"
dependencies = ["zlib>=1", "alpha>=1", "middle>=1"]
""",
        encoding="utf-8",
    )
    r1 = extract_key_resources(tmp_path)
    r2 = extract_key_resources(tmp_path)
    assert r1 == r2
    # Names of software rows are alphabetic.
    sw_names = [r.reagent_or_resource for r in r1 if r.category == ResourceCategory.software_algorithms]
    assert sw_names == sorted(sw_names, key=str.lower)


def test_extract_key_resources_raises_on_bad_root(tmp_path: Path) -> None:
    with pytest.raises(StarMethodsError):
        extract_key_resources(tmp_path / "does_not_exist")


# ─────────────────────────── 3. render Key Resources Table ────────────────────


def _stub_table_with_rows() -> StarMethodsTable:
    rows = (
        KeyResource(
            ResourceCategory.antibodies, "anti-CD11b", "Abcam", "ab133357"
        ),
        KeyResource(
            ResourceCategory.software_algorithms, "numpy", "PyPI", ">=1.24"
        ),
    )
    return StarMethodsTable(
        key_resources=rows,
        method_details_paragraphs={},
        quantification_paragraphs={},
        data_and_code_section="",
        n_recipes=0,
        venue="cell",
    )


def test_render_table_latex_contains_longtable_and_rows() -> None:
    table = _stub_table_with_rows()
    out = render_star_methods_table_latex(table)
    assert "longtable" in out
    assert "anti-CD11b" in out
    assert "numpy" in out
    # Category headers present.
    assert "Antibodies" in out
    assert "Software and Algorithms" in out


def test_render_table_latex_escapes_special_chars() -> None:
    table = StarMethodsTable(
        key_resources=(
            KeyResource(
                ResourceCategory.other,
                "A & B",
                "100% pure",
                "cat_no",
            ),
        ),
        method_details_paragraphs={},
        quantification_paragraphs={},
        data_and_code_section="",
        n_recipes=0,
    )
    out = render_star_methods_table_latex(table)
    assert r"\&" in out
    assert r"\%" in out
    assert r"\_" in out


def test_render_table_markdown_contains_pipes_and_rows() -> None:
    table = _stub_table_with_rows()
    out = render_star_methods_table_markdown(table)
    assert "|" in out
    assert "anti-CD11b" in out
    assert "numpy" in out


def test_render_table_empty_table_yields_placeholder() -> None:
    table = StarMethodsTable(
        key_resources=(),
        method_details_paragraphs={},
        quantification_paragraphs={},
        data_and_code_section="",
        n_recipes=0,
    )
    latex = render_star_methods_table_latex(table)
    md = render_star_methods_table_markdown(table)
    assert "No resources detected" in latex
    assert "No resources detected" in md


# ─────────────────────────── 4. method-details / quantification ───────────────


def test_render_method_details_with_missing_recipe_silently_skips() -> None:
    """Unknown recipe names produce no paragraphs but don't raise."""
    plan = _StubPlan(
        figures=(
            _StubFigure(
                figure_id="1",
                panels=(_StubPanel(recipe_full_name="nonexistent.recipe"),),
            ),
        )
    )
    out = render_method_details_section(plan)
    assert out == {}


def test_render_quantification_with_missing_recipe_silently_skips() -> None:
    plan = _StubPlan(
        figures=(
            _StubFigure(
                figure_id="1",
                panels=(_StubPanel(recipe_full_name="nonexistent.recipe"),),
            ),
        )
    )
    out = render_quantification_section(plan)
    assert out == {}


def test_render_method_details_with_real_recipe_emits_paragraph() -> None:
    """Pull a real registered recipe and verify a paragraph is rendered."""
    from panelforge_figures.core.contract import ensure_all_imported, list_recipes

    ensure_all_imported()
    recipes = list_recipes()
    if not recipes:
        pytest.skip("no recipes registered")
    full_name = recipes[0].full_name
    plan = _StubPlan(
        figures=(
            _StubFigure(
                figure_id="1",
                panels=(_StubPanel(recipe_full_name=full_name),),
            ),
        )
    )
    out = render_method_details_section(plan)
    # At least one family-keyed paragraph should appear.
    assert len(out) >= 1
    for paragraph in out.values():
        assert paragraph.strip().endswith(".")
        assert "panels in the" in paragraph.lower() or "addressed" in paragraph.lower()


def test_render_quantification_with_real_recipe_emits_paragraph() -> None:
    from panelforge_figures.core.contract import ensure_all_imported, list_recipes

    ensure_all_imported()
    recipes = list_recipes()
    if not recipes:
        pytest.skip("no recipes registered")
    full_name = recipes[0].full_name
    plan = _StubPlan(
        figures=(
            _StubFigure(
                figure_id="1",
                panels=(_StubPanel(recipe_full_name=full_name),),
            ),
        )
    )
    out = render_quantification_section(plan)
    assert len(out) >= 1


def test_render_method_details_with_none_plan_returns_empty_dict() -> None:
    out = render_method_details_section(None)
    assert out == {}


# ─────────────────────────── 5. generate_star_methods (end-to-end) ────────────


def test_generate_star_methods_no_plan(tmp_path: Path) -> None:
    """End-to-end: project root only, no plan, no errors."""
    (tmp_path / "pyproject.toml").write_text(
        """\
[project]
name = "p"
version = "0.0.1"
dependencies = ["numpy>=1"]
""",
        encoding="utf-8",
    )
    table = generate_star_methods(tmp_path, None, venue="cell", format="latex")
    assert isinstance(table, StarMethodsTable)
    assert len(table.key_resources) >= 1
    # Data and code section is always populated (TODO if nothing found).
    assert table.data_and_code_section
    assert "TODO" in table.data_and_code_section or "deposited" in table.data_and_code_section


def test_generate_star_methods_invalid_venue_raises(tmp_path: Path) -> None:
    with pytest.raises(StarMethodsError):
        generate_star_methods(tmp_path, None, venue="bogus", format="latex")


def test_generate_star_methods_invalid_format_raises(tmp_path: Path) -> None:
    with pytest.raises(StarMethodsError):
        generate_star_methods(tmp_path, None, venue="cell", format="rtf")


# ─────────────────────────── 6. CLI smoke ─────────────────────────────────────


def test_cli_star_methods_smoke(tmp_path: Path) -> None:
    """``figures star-methods <root>`` exits 0 and prints a longtable."""
    (tmp_path / "pyproject.toml").write_text(
        """\
[project]
name = "p"
version = "0.0.1"
dependencies = ["numpy>=1"]
""",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli_main, ["star-methods", str(tmp_path), "--format", "markdown"]
    )
    assert result.exit_code == 0, result.output
    assert "numpy" in result.output


def test_cli_star_methods_writes_out(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """\
[project]
name = "p"
version = "0.0.1"
""",
        encoding="utf-8",
    )
    out_path = tmp_path / "star_methods.md"
    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        [
            "star-methods",
            str(tmp_path),
            "--format", "markdown",
            "--out", str(out_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert out_path.is_file()
    body = out_path.read_text(encoding="utf-8")
    assert "Reagent or Resource" in body
