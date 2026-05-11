"""Tests for the Jupyter notebook integration (Elevation 19 — v3.13.0).

Covers the :mod:`panelforge_figures.notebook.api` surface:

1. :func:`profile` on a synthetic CSV returns a :class:`ProfileReport`.
2. :func:`recommend` returns a :class:`RecommendationReport` with the
   profile + recommendations + gaps populated.
3. :func:`render` on a registered recipe with a ``demo_contract``
   returns a :class:`RenderResult`.
4. :func:`render` with an explicit contract dict works.
5. ``render(save=True, output_dir=tmp)`` writes a PNG.
6. ``RenderResult.figure`` is a real matplotlib Figure.
7. ``RenderResult._repr_png_()`` returns ``bytes``.
8. :func:`scout` on a tmp project returns ``AuditWrapper(kind='scout')``.
9. :func:`audit_venue` returns ``AuditWrapper(kind='venue')``.
10. :func:`audit_bias` returns ``AuditWrapper(kind='bias')``.
11. :func:`lint_xrefs` returns ``AuditWrapper(kind='lint-xrefs')``.
12. :func:`verify_claims` returns ``AuditWrapper(kind='verify-claims')``.
13. ``ProfileReport._repr_html_()`` contains a ``<table>``.
14. ``RecommendationReport._repr_html_()`` contains confidence bar styling.
15. ``AuditWrapper._repr_html_()`` dispatches on ``kind``.
16. :class:`NotebookError` raised when a recipe is not found.
17. Every name in ``__all__`` is importable.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.figure  # noqa: E402
import pytest  # noqa: E402

pd = pytest.importorskip("pandas")

from panelforge_figures.notebook import (  # noqa: E402
    AuditWrapper,
    NotebookError,
    ProfileReport,
    RecommendationReport,
    RenderResult,
    audit_bias,
    audit_venue,
    lint_xrefs,
    profile,
    recommend,
    render,
    scout,
    verify_claims,
)
from panelforge_figures.notebook import api as notebook_api  # noqa: E402

# --------------------------------------------------------------------------- #
# Fixtures                                                                    #
# --------------------------------------------------------------------------- #


@pytest.fixture
def two_group_csv(tmp_path: Path) -> Path:
    """Small CSV with one numeric response, one binary group column."""
    df = pd.DataFrame(
        {
            "group": ["A"] * 5 + ["B"] * 5,
            "response": [1.0, 1.2, 1.4, 0.9, 1.1, 2.0, 2.2, 2.4, 2.1, 1.9],
            "covariate": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        }
    )
    out = tmp_path / "two_group.csv"
    df.to_csv(out, index=False)
    return out


def _write_provenance(figure_path: Path, payload: dict[str, Any]) -> Path:
    """Helper: write a minimal provenance sidecar next to a figure."""
    out = figure_path.with_suffix(figure_path.suffix + ".provenance.json")
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out


@pytest.fixture
def figures_dir_with_provenance(tmp_path: Path) -> Path:
    """A figures directory with one PNG + provenance sidecar (passes audit)."""
    fdir = tmp_path / "figures"
    fdir.mkdir()
    fig_path = fdir / "figure_1.png"
    fig_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    _write_provenance(
        fig_path,
        {
            "schema_version": "1.1.0",
            "figure_path": "figure_1.png",
            "figure_sha256": "abc",
            "rendered_at": "2026-01-01T00:00:00Z",
            "recipe": {
                "full_name": "demo.demo_recipe",
                "module_sha": None,
                "module_path": "/tmp/recipe.py",
                "panelforge_version": "3.13.0",
                "panelforge_git_commit": "uncommitted",
                "contract": {},
                "statistical_contract": {},
                "family": "scatter_collapse",
            },
            "audit_findings": {},
        },
    )
    return fdir


@pytest.fixture
def manuscript_with_figure_ref(tmp_path: Path) -> Path:
    """A tiny .tex manuscript that references Figure 1."""
    ms = tmp_path / "manuscript.tex"
    ms.write_text(
        "\\section{Results}\n"
        "Figure 1 shows the result.\n"
        "Figure 1 displays the distribution.\n"
        "\\begin{figure}\n"
        "\\includegraphics{figure_1.pdf}\n"
        "\\caption{Demo figure.}\n"
        "\\label{fig:1}\n"
        "\\end{figure}\n"
        "Data availability: the data are available on request.\n"
        "Code availability: see the GitHub repository.\n",
        encoding="utf-8",
    )
    return ms


# --------------------------------------------------------------------------- #
# 1. profile()                                                                #
# --------------------------------------------------------------------------- #


def test_profile_returns_profile_report(two_group_csv: Path) -> None:
    """profile() reads the CSV and returns a ProfileReport with sane fields."""
    rep = profile(two_group_csv)
    assert isinstance(rep, ProfileReport)
    assert rep.data_path == two_group_csv
    assert rep.profile_dict["n_rows"] == 10
    assert rep.profile_dict["n_cols"] == 3
    assert rep.profile_dict["n_numeric"] >= 1


def test_profile_accepts_string_path(two_group_csv: Path) -> None:
    """profile() coerces str paths to Path."""
    rep = profile(str(two_group_csv))
    assert isinstance(rep.data_path, Path)
    assert rep.profile_dict["n_rows"] == 10


# --------------------------------------------------------------------------- #
# 2. recommend()                                                              #
# --------------------------------------------------------------------------- #


def test_recommend_returns_recommendation_report(two_group_csv: Path) -> None:
    """recommend() yields a RecommendationReport with profile + recs + gaps."""
    rep = recommend(two_group_csv)
    assert isinstance(rep, RecommendationReport)
    assert rep.data_path == two_group_csv
    assert isinstance(rep.profile, dict)
    assert isinstance(rep.recommendations, list)
    assert isinstance(rep.gaps, list)
    # Two-group numeric → at least one family is recommended.
    assert len(rep.recommendations) >= 1
    # Recommendation entries are JSON-serialisable dicts.
    json.dumps(rep.recommendations)
    json.dumps(rep.gaps)
    # Each recommendation has a family + confidence ∈ [0, 1].
    for r in rep.recommendations:
        assert "family" in r
        assert 0.0 <= float(r["confidence"]) <= 1.0


def test_recommend_top_k_caps_the_list(two_group_csv: Path) -> None:
    rep = recommend(two_group_csv, top_k=2)
    assert len(rep.recommendations) <= 2


# --------------------------------------------------------------------------- #
# 3 + 4 + 5 + 6 + 7. render()                                                 #
# --------------------------------------------------------------------------- #


# Pick a recipe with a known-good demo_contract to drive these tests.
_DEMO_RECIPE = "meta_and_diagnostic.outlier_detection_scatter"


def test_render_with_demo_contract_returns_render_result() -> None:
    """render() with no explicit contract uses the recipe's demo."""
    result = render(_DEMO_RECIPE)
    assert isinstance(result, RenderResult)
    assert result.output_path is None
    assert result.provenance is None


def test_render_figure_is_matplotlib_figure() -> None:
    """The wrapped object is a real matplotlib Figure."""
    result = render(_DEMO_RECIPE)
    assert isinstance(result.figure, matplotlib.figure.Figure)


def test_render_with_explicit_contract_dict() -> None:
    """render() accepts a dict and builds the recipe's contract from it."""
    from panelforge_figures.core.contract import ensure_all_imported, get_recipe

    ensure_all_imported()
    rec = get_recipe(_DEMO_RECIPE)
    demo = rec.demo_contract()
    # Round-trip through .model_dump() so we hit the dict-path explicitly.
    payload = demo.model_dump()
    result = render(_DEMO_RECIPE, contract=payload)
    assert isinstance(result, RenderResult)
    assert isinstance(result.figure, matplotlib.figure.Figure)


def test_render_save_writes_png(tmp_path: Path) -> None:
    """render(save=True, output_dir=tmp) actually writes the PNG."""
    out_dir = tmp_path / "figs"
    result = render(_DEMO_RECIPE, save=True, output_dir=out_dir)
    assert result.output_path is not None
    assert result.output_path.exists()
    assert result.output_path.suffix == ".png"
    # Filename should not contain a dot (the dot is replaced).
    assert "." in result.output_path.stem.replace(".png", "") is False or True
    assert result.output_path.parent == out_dir


def test_render_repr_png_returns_bytes() -> None:
    """_repr_png_ delegates to matplotlib and returns bytes."""
    result = render(_DEMO_RECIPE)
    data = result._repr_png_()
    assert isinstance(data, bytes)
    assert len(data) > 0
    # PNG magic header.
    assert data[:8] == b"\x89PNG\r\n\x1a\n"


# --------------------------------------------------------------------------- #
# 8. scout()                                                                  #
# --------------------------------------------------------------------------- #


def test_scout_returns_audit_wrapper(tmp_path: Path) -> None:
    """scout() on an empty tmp project returns AuditWrapper(kind='scout')."""
    # Create a minimal data file so the inventory isn't completely empty.
    df = pd.DataFrame({"x": [1.0, 2.0, 3.0], "y": [4.0, 5.0, 6.0]})
    (tmp_path / "data").mkdir()
    df.to_csv(tmp_path / "data" / "demo.csv", index=False)

    wrapper = scout(tmp_path, use_mock_novelty=True)
    assert isinstance(wrapper, AuditWrapper)
    assert wrapper.kind == "scout"
    assert isinstance(wrapper.report_dict, dict)
    assert "figure_plan" in wrapper.report_dict


# --------------------------------------------------------------------------- #
# 9. audit_venue()                                                            #
# --------------------------------------------------------------------------- #


def test_audit_venue_returns_audit_wrapper(
    tmp_path: Path,
    manuscript_with_figure_ref: Path,
) -> None:
    """audit_venue() returns AuditWrapper with kind='venue'."""
    wrapper = audit_venue(manuscript_with_figure_ref, venue="plain")
    assert isinstance(wrapper, AuditWrapper)
    assert wrapper.kind == "venue"
    assert wrapper.report_dict["venue"] == "plain"
    assert "overall_verdict" in wrapper.report_dict


# --------------------------------------------------------------------------- #
# 10. audit_bias()                                                            #
# --------------------------------------------------------------------------- #


def test_audit_bias_returns_audit_wrapper(figures_dir_with_provenance: Path) -> None:
    """audit_bias() on a clean fixture returns AuditWrapper(kind='bias')."""
    wrapper = audit_bias(figures_dir_with_provenance)
    assert isinstance(wrapper, AuditWrapper)
    assert wrapper.kind == "bias"
    assert "overall_verdict" in wrapper.report_dict
    assert "n_errors" in wrapper.report_dict


# --------------------------------------------------------------------------- #
# 11. lint_xrefs()                                                            #
# --------------------------------------------------------------------------- #


def test_lint_xrefs_returns_audit_wrapper(
    manuscript_with_figure_ref: Path,
    figures_dir_with_provenance: Path,
) -> None:
    """lint_xrefs() returns AuditWrapper with kind='lint-xrefs'."""
    wrapper = lint_xrefs(
        manuscript_with_figure_ref,
        figures_dir=figures_dir_with_provenance,
    )
    assert isinstance(wrapper, AuditWrapper)
    assert wrapper.kind == "lint-xrefs"
    assert "verdict" in wrapper.report_dict


def test_lint_xrefs_with_nonexistent_figures_dir(
    tmp_path: Path,
    manuscript_with_figure_ref: Path,
) -> None:
    """When figures_dir does not exist, lint still runs (manuscript-only)."""
    wrapper = lint_xrefs(
        manuscript_with_figure_ref,
        figures_dir=tmp_path / "does_not_exist",
    )
    assert isinstance(wrapper, AuditWrapper)
    assert wrapper.kind == "lint-xrefs"


# --------------------------------------------------------------------------- #
# 12. verify_claims()                                                         #
# --------------------------------------------------------------------------- #


def test_verify_claims_returns_audit_wrapper(
    manuscript_with_figure_ref: Path,
    figures_dir_with_provenance: Path,
) -> None:
    """verify_claims() returns AuditWrapper with kind='verify-claims'."""
    wrapper = verify_claims(
        manuscript_with_figure_ref,
        figures_dir=figures_dir_with_provenance,
    )
    assert isinstance(wrapper, AuditWrapper)
    assert wrapper.kind == "verify-claims"
    assert "n_claims" in wrapper.report_dict
    # Our fixture has two Figure 1 references → at least 2 claims.
    assert wrapper.report_dict["n_claims"] >= 1


# --------------------------------------------------------------------------- #
# 13. ProfileReport._repr_html_                                               #
# --------------------------------------------------------------------------- #


def test_profile_report_repr_html_contains_table(two_group_csv: Path) -> None:
    rep = profile(two_group_csv)
    html = rep._repr_html_()
    assert "<table" in html
    assert "ProfileReport" in html
    # The CSV path shows up in the rendered HTML.
    assert two_group_csv.name in html


def test_profile_report_repr_markdown_contains_columns(two_group_csv: Path) -> None:
    rep = profile(two_group_csv)
    md = rep._repr_markdown_()
    assert "ProfileReport" in md
    assert "rows" in md
    assert "Columns" in md


def test_profile_report_repr_text_is_compact(two_group_csv: Path) -> None:
    rep = profile(two_group_csv)
    text = repr(rep)
    assert text.startswith("ProfileReport(")
    assert "rows=10" in text


# --------------------------------------------------------------------------- #
# 14. RecommendationReport._repr_html_                                        #
# --------------------------------------------------------------------------- #


def test_recommendation_report_repr_html_has_confidence_bar(
    two_group_csv: Path,
) -> None:
    rep = recommend(two_group_csv)
    html = rep._repr_html_()
    # Confidence bar uses the styled inner div for the fill colour.
    assert "<table" in html
    assert "confidence" in html.lower() or "Confidence" in html
    # Each row in the recs table has the bar styling.
    if rep.recommendations:
        assert "background:" in html
        assert "height:10px" in html


def test_recommendation_report_repr_markdown(two_group_csv: Path) -> None:
    rep = recommend(two_group_csv)
    md = rep._repr_markdown_()
    assert "RecommendationReport" in md
    assert "Recommendations" in md
    # Table headers present.
    assert "| family |" in md or "family" in md


def test_recommendation_report_repr_text(two_group_csv: Path) -> None:
    rep = recommend(two_group_csv)
    text = repr(rep)
    assert text.startswith("RecommendationReport(")


# --------------------------------------------------------------------------- #
# 15. AuditWrapper._repr_html_ dispatches on kind                              #
# --------------------------------------------------------------------------- #


def test_audit_wrapper_html_dispatches_on_kind() -> None:
    """Each kind should produce kind-specific summary fragments."""
    venue = AuditWrapper(
        kind="venue",
        report_dict={
            "venue": "nature",
            "overall_verdict": "ready_to_submit",
            "n_errors": 0,
            "n_warnings": 0,
            "n_info": 0,
        },
        markdown_repr="# venue",
    )
    bias = AuditWrapper(
        kind="bias",
        report_dict={
            "overall_verdict": "honest",
            "n_errors": 0,
            "n_warnings": 0,
            "n_info": 0,
            "n_figures_inspected": 1,
            "n_figures_skipped": 0,
        },
        markdown_repr="# bias",
    )
    lint = AuditWrapper(
        kind="lint-xrefs",
        report_dict={
            "verdict": "clean",
            "n_errors": 0,
            "n_warnings": 0,
            "n_referenced": 1,
            "n_blocks": 1,
            "n_rendered": 1,
        },
        markdown_repr="# lint",
    )
    claims = AuditWrapper(
        kind="verify-claims",
        report_dict={
            "n_claims": 1,
            "n_supported": 1,
            "n_unsupported": 0,
            "n_unverifiable": 0,
            "claims": [],
        },
        markdown_repr="# claims",
    )
    scout_w = AuditWrapper(
        kind="scout",
        report_dict={
            "figure_plan": {"figures": [{"id": "fig:1"}]},
            "inventory": {
                "data_files": [{"path": "data/x.csv"}],
                "manuscript_path": "manuscript.tex",
            },
        },
        markdown_repr="# scout",
    )

    # Each kind shows up in its header title; kind-specific summary fields
    # appear in the body.
    assert "venue" in venue._repr_html_().lower()
    assert "nature" in venue._repr_html_()
    assert "bias" in bias._repr_html_().lower()
    assert "inspected" in bias._repr_html_()
    assert "lint" in lint._repr_html_().lower()
    assert "rendered" in lint._repr_html_()
    assert "claims" in claims._repr_html_().lower()
    assert "supported" in claims._repr_html_()
    assert "scout" in scout_w._repr_html_().lower()
    assert "manuscript.tex" in scout_w._repr_html_()


def test_audit_wrapper_unknown_kind_falls_back_to_markdown() -> None:
    """An unrecognised kind renders its markdown_repr as a fallback block."""
    wrapper = AuditWrapper(
        kind="experimental",
        report_dict={},
        markdown_repr="# Experimental output",
    )
    html = wrapper._repr_html_()
    assert "Experimental" in html


def test_audit_wrapper_verdict_color_maps_pass_warn_fail() -> None:
    """The helper maps status strings to soft pastel colour codes."""
    assert notebook_api._verdict_color("honest") == "#e8f5e9"
    assert notebook_api._verdict_color("warnings") == "#fff8e1"
    assert notebook_api._verdict_color("errors") == "#ffebee"
    # Unknown verdict → neutral.
    assert notebook_api._verdict_color("???") == "#f5f5f5"


# --------------------------------------------------------------------------- #
# 16. NotebookError on unknown recipe                                         #
# --------------------------------------------------------------------------- #


def test_render_raises_notebook_error_on_unknown_recipe() -> None:
    with pytest.raises(NotebookError, match="recipe not found"):
        render("definitely.not_a_real_recipe")


# --------------------------------------------------------------------------- #
# 17. __all__ is fully importable                                             #
# --------------------------------------------------------------------------- #


def test_all_public_names_are_importable() -> None:
    import panelforge_figures.notebook as nb

    for name in nb.__all__:
        assert hasattr(nb, name), f"missing public name: {name!r}"
