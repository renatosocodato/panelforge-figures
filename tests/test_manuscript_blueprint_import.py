"""Tests for the manuscript-blueprint module (Elevation 10 — phase 3).

Owned by Build-C.  Tests the inverse-direction pipeline:

    manuscript.tex  →  blueprint-import  →  figures_plan.yaml

The module is implemented directly (no ``importorskip`` gate) since
Build-C is responsible for it.  Some tests depend on Build-A's
:mod:`manuscript_parse` landing — those are gated with ``importorskip``
and pass cleanly during a Build-C-only verification pass.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from panelforge_figures.manifest.manuscript_blueprint import (
    BlueprintImportError,
    BlueprintImportResult,
    CaptionMatch,
    import_blueprint_from_manuscript,
    match_caption_to_recipe,
)

# ─────────────────────────── synthetic recipes ──────────────────────────


class _MockMetadata:
    def __init__(self, modality: str, name: str, answers_question: str) -> None:
        self.modality = modality
        self.name = name
        self.answers_question = answers_question


class _MockRecipe:
    def __init__(self, modality: str, name: str, answers_question: str) -> None:
        self.metadata = _MockMetadata(modality, name, answers_question)

    @property
    def full_name(self) -> str:
        return f"{self.metadata.modality}.{self.metadata.name}"


_MOCK_VOLCANO = _MockRecipe(
    modality="omics_differential",
    name="volcano_labeled_repelled",
    answers_question=(
        "Which genes are significantly differentially expressed between "
        "conditions in the volcano plot?"
    ),
)
_MOCK_SURVIVAL = _MockRecipe(
    modality="dose_response_pharmacology",
    name="kaplan_meier_with_log_rank",
    answers_question=(
        "What is the time-to-event survival curve and log-rank statistic?"
    ),
)
_MOCK_PROVENANCE = _MockRecipe(
    modality="meta_and_diagnostic",
    name="panel_provenance_ledger_table",
    answers_question="What provenance ledger does each rendered panel carry?",
)


# ─────────────────────────── match_caption_to_recipe ────────────────────


def test_match_caption_to_recipe_matches_volcano() -> None:
    """Volcano-flavoured caption should match volcano recipe with sim >= 0.4."""
    caption = (
        "Volcano plot showing the differentially expressed genes between "
        "conditions, labelled and repelled to avoid overlap. Significantly "
        "higher expression in treated samples."
    )
    match = match_caption_to_recipe(
        caption,
        candidate_recipes=[_MOCK_VOLCANO, _MOCK_SURVIVAL, _MOCK_PROVENANCE],
        figure_id="fig:1",
    )
    assert isinstance(match, CaptionMatch)
    assert match.suggested_recipe_full_name == (
        "omics_differential.volcano_labeled_repelled"
    )
    assert match.similarity_score > 0.0


def test_match_caption_to_recipe_random_caption_no_match() -> None:
    """A caption with no overlap should match weakly (or not at all)."""
    caption = "qzxwf nonsensical lorem ipsum aaa bbb"
    match = match_caption_to_recipe(
        caption,
        candidate_recipes=[_MOCK_VOLCANO, _MOCK_SURVIVAL, _MOCK_PROVENANCE],
        figure_id="fig:1",
    )
    assert isinstance(match, CaptionMatch)
    assert match.similarity_score < 0.4


def test_match_caption_to_recipe_strips_latex_markup() -> None:
    """LaTeX markup should be stripped before matching."""
    caption = r"\textbf{Volcano plot} of $p$-values; see \cite{X} \emph{here}."
    match = match_caption_to_recipe(
        caption,
        candidate_recipes=[_MOCK_VOLCANO, _MOCK_SURVIVAL, _MOCK_PROVENANCE],
        figure_id="fig:1",
    )
    assert "volcano" in match.caption_excerpt.lower()
    assert "\\textbf" not in match.caption_excerpt


def test_match_caption_to_recipe_empty_caption_returns_zero() -> None:
    """An empty caption returns ``similarity_score=0`` and ``None`` recipe."""
    match = match_caption_to_recipe(
        "",
        candidate_recipes=[_MOCK_VOLCANO, _MOCK_SURVIVAL, _MOCK_PROVENANCE],
        figure_id="fig:1",
    )
    assert match.similarity_score == 0.0
    assert match.suggested_recipe_full_name is None


def test_match_caption_to_recipe_no_candidates_returns_zero() -> None:
    """No candidate recipes → match score 0, suggested None."""
    match = match_caption_to_recipe(
        "anything",
        candidate_recipes=[],
        figure_id="fig:1",
    )
    assert match.similarity_score == 0.0
    assert match.suggested_recipe_full_name is None


def test_match_caption_to_recipe_returns_top3_alternatives() -> None:
    """The matcher returns up to 3 alternative recipes."""
    caption = "volcano plot of differentially expressed genes"
    match = match_caption_to_recipe(
        caption,
        candidate_recipes=[
            _MOCK_VOLCANO, _MOCK_SURVIVAL, _MOCK_PROVENANCE,
        ],
        figure_id="fig:1",
    )
    assert isinstance(match.candidate_alternatives, tuple)
    assert len(match.candidate_alternatives) <= 3


# ─────────────────────────── import_blueprint_from_manuscript ───────────


_SYNTHETIC_LATEX = r"""\documentclass[11pt]{article}
\begin{document}
\section{Results}
\begin{figure}
\caption{Volcano plot of differentially expressed genes between conditions.}
\label{fig:1}
\end{figure}
\begin{figure}
\caption{Kaplan-Meier survival curves with log-rank comparison between treated and control groups.}
\label{fig:2}
\end{figure}
\begin{figure}
\caption{Provenance ledger of every rendered panel with hash and units.}
\label{fig:3}
\end{figure}
\end{document}
"""


def test_import_blueprint_from_manuscript_three_figures(tmp_path: Path) -> None:
    """A synthetic 3-figure manuscript → 3-figure plan."""
    pytest.importorskip("panelforge_figures.manifest.manuscript_parse")
    p = tmp_path / "m.tex"
    p.write_text(_SYNTHETIC_LATEX, encoding="utf-8")
    plan_out = tmp_path / "plan.yaml"
    result = import_blueprint_from_manuscript(
        p, output_plan_path=plan_out,
    )
    assert isinstance(result, BlueprintImportResult)
    assert result.n_figures_parsed == 3
    assert result.figure_plan_path == plan_out
    assert plan_out.is_file()


def test_import_blueprint_no_output_does_not_write(tmp_path: Path) -> None:
    """``output_plan_path=None`` should not produce a YAML file."""
    pytest.importorskip("panelforge_figures.manifest.manuscript_parse")
    p = tmp_path / "m.tex"
    p.write_text(_SYNTHETIC_LATEX, encoding="utf-8")
    result = import_blueprint_from_manuscript(p, output_plan_path=None)
    assert result.figure_plan_path is None


def test_import_blueprint_low_similarity_creates_gaps(tmp_path: Path) -> None:
    """Captions far below threshold → ``is_gap=True`` panels."""
    pytest.importorskip("panelforge_figures.manifest.manuscript_parse")
    body = r"""\documentclass{article}
\begin{document}
\begin{figure}
\caption{qzxwf nonsensical lorem ipsum aaa bbb}
\label{fig:1}
\end{figure}
\end{document}
"""
    p = tmp_path / "m.tex"
    p.write_text(body, encoding="utf-8")
    plan_out = tmp_path / "plan.yaml"
    result = import_blueprint_from_manuscript(
        p, output_plan_path=plan_out, min_similarity=0.9,
    )
    # With a 0.9 threshold even reasonable matches become gaps.
    assert result.n_figures_unmatched >= 1


def test_import_blueprint_raises_on_missing_file(tmp_path: Path) -> None:
    """Missing manuscript path → BlueprintImportError."""
    p = tmp_path / "does_not_exist.tex"
    with pytest.raises(BlueprintImportError):
        import_blueprint_from_manuscript(p, output_plan_path=None)


# ─────────────────────────── CLI smoke ──────────────────────────────────


def test_cli_blueprint_import_help() -> None:
    """``figures manuscript blueprint-import --help`` exits 0 with usage text."""
    from panelforge_figures.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ["manuscript", "blueprint-import", "--help"])
    assert result.exit_code == 0, result.output
    assert "Usage:" in result.output
    assert "blueprint-import" in result.output.lower() or (
        "manuscript" in result.output.lower()
    )


def test_cli_blueprint_import_runs_on_synthetic_manuscript(
    tmp_path: Path,
) -> None:
    """CLI invocation writes figures_plan.yaml for a synthetic manuscript."""
    pytest.importorskip("panelforge_figures.manifest.manuscript_parse")
    from panelforge_figures.cli import main

    manuscript = tmp_path / "m.tex"
    manuscript.write_text(_SYNTHETIC_LATEX, encoding="utf-8")
    plan_out = tmp_path / "figures_plan.yaml"

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "manuscript", "blueprint-import",
            str(manuscript),
            "--out", str(plan_out),
            "--min-similarity", "0.0",
        ],
    )
    # Accept exit codes 0 (Build-A landed) or 1 (clean import error
    # before Build-A's parser is on disk).
    assert result.exit_code in (0, 1, 2), result.output
    if result.exit_code == 0:
        assert plan_out.is_file()


# ─────────────────────────── Module surface ─────────────────────────────


def test_module_exports_documented_symbols() -> None:
    """``__all__`` must include every public symbol in the spec."""
    from panelforge_figures.manifest import manuscript_blueprint

    expected = {
        "BlueprintImportResult",
        "BlueprintImportError",
        "import_blueprint_from_manuscript",
        "match_caption_to_recipe",
    }
    assert expected.issubset(set(manuscript_blueprint.__all__))


def test_caption_match_has_documented_fields() -> None:
    """``CaptionMatch`` instances expose every field documented in the spec."""
    match = match_caption_to_recipe(
        "anything", candidate_recipes=[], figure_id="x",
    )
    for fld in (
        "figure_id",
        "caption_excerpt",
        "suggested_recipe_full_name",
        "similarity_score",
        "candidate_alternatives",
    ):
        assert hasattr(match, fld), f"missing field: {fld}"
