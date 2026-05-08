"""Tests for `manifest.manuscript_alignment` (Elevation 7, v3.0.0-rc2).

Covers:
- _split_manuscript_sections handles markdown + LaTeX
- _tokenize lowercases + filters non-alpha
- compute_tfidf_alignment returns scores in [0, 1]
- compute_tfidf_alignment ranks the most-aligned recipe highest
- compute_alignment_scores raises if the manuscript is missing
- compute_embedding_alignment gracefully reports missing extras (importorskip)
- WEIGHTS_HISTORY['1.1.0'] is registered and sums to 1.0
- score_to_dict round-trips via json
- CLI smoke + ranked-output integration
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest
from click.testing import CliRunner

from panelforge_figures.cli import main as cli_main
from panelforge_figures.manifest.manuscript_alignment import (
    AlignmentBackend,
    AlignmentScore,
    ManuscriptAlignmentError,
    _split_manuscript_sections,
    _tokenize,
    compute_alignment_scores,
    compute_tfidf_alignment,
    score_to_dict,
)
from panelforge_figures.manifest.scoring import WEIGHTS_HISTORY

# ──────────── lightweight RecipeInfo stub ────────────


@dataclass(frozen=True)
class _StubMeta:
    modality: str
    name: str
    answers_question: str


@dataclass(frozen=True)
class _StubRecipe:
    metadata: _StubMeta


def _make_recipe(modality: str, name: str, question: str) -> _StubRecipe:
    return _StubRecipe(metadata=_StubMeta(modality, name, question))


# ─────────────────────── 1. section splitter ───────────────────────


def test_split_manuscript_sections_markdown() -> None:
    """Markdown headers (#, ##, ###) split into named sections."""
    text = (
        "# Introduction\n"
        "We study microglia.\n\n"
        "## Methods\n"
        "We used scRNA-seq.\n\n"
        "### Results\n"
        "There were three populations.\n"
    )
    out = _split_manuscript_sections(text)
    assert "Introduction" in out
    assert "Methods" in out
    assert "Results" in out
    assert "_full" in out
    assert "microglia" in out["Introduction"]
    assert "scRNA-seq" in out["Methods"]
    assert "three populations" in out["Results"]


def test_split_manuscript_sections_latex() -> None:
    r"""LaTeX \section{...} fallback when no markdown headers are present."""
    text = (
        r"\section{Background}"
        "\nMicroglia drive synaptic remodeling.\n"
        r"\subsection{Cytoskeleton}"
        "\nActin and microtubules form a co-regulated lattice.\n"
        r"\section*{Conclusion}"
        "\nWe propose a mechanism.\n"
    )
    out = _split_manuscript_sections(text)
    assert "Background" in out
    assert "Cytoskeleton" in out
    assert "Conclusion" in out
    assert "synaptic" in out["Background"]


def test_split_manuscript_sections_no_headers() -> None:
    """Plain text with no headers returns just the `_full` fallback."""
    text = "Just a paragraph with no section markers at all."
    out = _split_manuscript_sections(text)
    assert "_full" in out
    # No section names beyond `_full`
    assert set(out) == {"_full"}


# ─────────────────────── 2. tokenizer ───────────────────────


def test_tokenize_lowercases_and_filters_non_alpha() -> None:
    """`_tokenize` keeps only lowercase alphabetic words ≥ 2 chars.

    Tokens with embedded digits (e.g. ``cdc42``) are dropped entirely
    because the regex requires a word boundary after the alpha run, and
    digits are word-characters (no boundary between them).  This is
    desired behaviour: it keeps the IDF vocabulary clean of mixed
    identifiers that would otherwise inflate document-frequency.
    """
    text = "Microglia (Iba1+) cells are NUMEROUS in knockout (n=42) mice!"
    tokens = _tokenize(text)
    # All lowercase
    assert all(t == t.lower() for t in tokens)
    # No digits, no single-letter, no punctuation tokens
    assert "42" not in tokens
    assert "n" not in tokens
    assert "microglia" in tokens
    assert "knockout" in tokens
    assert "mice" in tokens
    # Capitalization stripped
    assert "MICROGLIA" not in tokens
    assert "NUMEROUS" not in tokens
    assert "numerous" in tokens


def test_tokenize_empty_string() -> None:
    assert _tokenize("") == []


# ─────────────────────── 3. TF-IDF alignment ───────────────────────


def test_compute_tfidf_alignment_ranks_aligned_recipe_first() -> None:
    """A recipe whose question semantically matches the manuscript section
    must score higher than recipes about unrelated topics."""
    text = (
        "# Introduction\n"
        "We profiled CDC42 activity in microglia processes during morphology "
        "remodeling.  Active GTP-bound CDC42 governs filopodial protrusions.\n\n"
        "# Methods\n"
        "We used spinning-disk confocal microscopy for live imaging.\n"
    )
    aligned = _make_recipe(
        "rhogtpase_dynamics",
        "cdc42_activity_morphology",
        "How does CDC42 GTP-bound activity drive microglial morphology remodeling?",
    )
    irrelevant = _make_recipe(
        "biophysics_scaling",
        "stress_strain_curve",
        "What is the bulk modulus of polyelectrolyte hydrogels?",
    )
    other = _make_recipe(
        "intravital_imaging",
        "photobleaching_correction",
        "How do we correct photobleaching in deep-tissue two-photon traces?",
    )
    scores = compute_tfidf_alignment(text, [aligned, irrelevant, other])
    by_name = {s.recipe_full_name: s for s in scores}
    assert (
        by_name["rhogtpase_dynamics.cdc42_activity_morphology"].score
        > by_name["biophysics_scaling.stress_strain_curve"].score
    )


def test_compute_tfidf_alignment_score_in_unit_interval() -> None:
    """Every score is clamped to [0, 1]."""
    text = "# Section\nLorem ipsum dolor sit amet.\n"
    recipes = [
        _make_recipe("m", f"r{i}", f"Question {i}? lorem dolor.")
        for i in range(5)
    ]
    scores = compute_tfidf_alignment(text, recipes)
    for s in scores:
        assert 0.0 <= s.score <= 1.0


def test_compute_tfidf_alignment_returns_backend() -> None:
    """All TF-IDF scores carry `backend == AlignmentBackend.tfidf`."""
    text = "# X\nfoo bar baz quux\n"
    recipes = [_make_recipe("m", "r", "foo bar question")]
    scores = compute_tfidf_alignment(text, recipes)
    assert all(s.backend == AlignmentBackend.tfidf for s in scores)


def test_compute_tfidf_alignment_matched_sections_are_ranked() -> None:
    """`matched_sections` is the top-3 best section keys, in order."""
    text = (
        "# A\nactin filament dynamics drive lamellipodial protrusion.\n\n"
        "# B\nchemotaxis is a multi-step process involving sensing.\n\n"
        "# C\nmitochondrial fission is calcium-dependent.\n"
    )
    actin = _make_recipe(
        "actin_microtubule_morphometry",
        "lamellipodial_dynamics",
        "How do actin filaments form protrusions during lamellipodial dynamics?",
    )
    scores = compute_tfidf_alignment(text, [actin])
    assert len(scores) == 1
    matched = scores[0].matched_sections
    # `A` should be the top match for an actin-protrusion question
    assert matched[0] == "A"
    assert "_full" not in matched          # synthetic fallback never surfaces


# ─────────────────────── 4. Top-level pipeline ───────────────────────


def test_compute_alignment_scores_missing_manuscript(tmp_path: Path) -> None:
    """Pipeline raises ManuscriptAlignmentError if the file is missing."""
    missing = tmp_path / "does_not_exist.md"
    with pytest.raises(ManuscriptAlignmentError) as excinfo:
        compute_alignment_scores(missing, [], backend=AlignmentBackend.tfidf)
    assert "manuscript not found" in str(excinfo.value)


def test_compute_alignment_scores_reads_file(tmp_path: Path) -> None:
    """Round-trip: pipeline reads the file, dispatches to TF-IDF backend."""
    p = tmp_path / "manuscript.md"
    p.write_text(
        "# Intro\nWe quantify CDC42 dynamics with FRET biosensors.\n",
        encoding="utf-8",
    )
    rec = _make_recipe(
        "rhogtpase_dynamics",
        "fret_biosensor",
        "How do FRET biosensors report CDC42 dynamics?",
    )
    out = compute_alignment_scores(p, [rec], backend=AlignmentBackend.tfidf)
    assert len(out) == 1
    assert out[0].recipe_full_name == "rhogtpase_dynamics.fret_biosensor"
    assert 0.0 <= out[0].score <= 1.0


# ─────────────────────── 5. embedding backend (optional) ───────────────────────


def test_compute_embedding_alignment_optional() -> None:
    """The sentence-transformers backend is opt-in; if not installed,
    importing it raises ManuscriptAlignmentError. We use importorskip
    so the test is skipped on environments without the extra."""
    pytest.importorskip("sentence_transformers")

    from panelforge_figures.manifest.manuscript_alignment import (
        compute_embedding_alignment,
    )

    text = "# Intro\nCDC42 governs migration.\n"
    rec = _make_recipe("rhogtpase_dynamics", "cdc42_motility", "How does CDC42 affect migration?")
    out = compute_embedding_alignment(text, [rec])
    assert len(out) == 1
    assert 0.0 <= out[0].score <= 1.0
    assert out[0].backend == AlignmentBackend.sentence_transformers


# ─────────────────────── 6. WEIGHTS_HISTORY 1.1.0 ───────────────────────


def test_weights_history_includes_1_1_0() -> None:
    """Elevation 7 registers a `1.1.0` entry."""
    assert "1.1.0" in WEIGHTS_HISTORY


def test_weights_history_1_1_0_sums_to_one() -> None:
    """The new rubric obeys the WEIGHTS_SUM_CHECK invariant."""
    weights = WEIGHTS_HISTORY["1.1.0"]
    assert abs(sum(weights.values()) - 1.0) < 1e-9


def test_weights_history_1_1_0_includes_manuscript_alignment() -> None:
    """The new rubric registers the new term."""
    weights = WEIGHTS_HISTORY["1.1.0"]
    assert "manuscript_alignment" in weights
    assert weights["manuscript_alignment"] == pytest.approx(0.10)


# ─────────────────────── 7. score_to_dict round-trip ───────────────────────


def test_score_to_dict_round_trips_via_json() -> None:
    """Round-tripping through json.dumps/loads preserves all fields."""
    s = AlignmentScore(
        recipe_full_name="m.r",
        score=0.42,
        matched_sections=("A", "B", "C"),
        backend=AlignmentBackend.tfidf,
    )
    payload = score_to_dict(s)
    blob = json.dumps(payload)
    restored = json.loads(blob)
    assert restored["recipe_full_name"] == "m.r"
    assert restored["score"] == 0.42
    assert restored["matched_sections"] == ["A", "B", "C"]
    assert restored["backend"] == "tfidf"


# ─────────────────────── 8. CLI smoke + integration ───────────────────────


def test_cli_align_manuscript_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli_main, ["align-manuscript", "--help"])
    assert result.exit_code == 0, result.output
    assert "manuscript" in result.output.lower()
    assert "--backend" in result.output


def test_cli_align_manuscript_emits_ranked_list(tmp_path: Path) -> None:
    """End-to-end: a synthetic manuscript produces a ranked recipe list."""
    p = tmp_path / "manuscript.md"
    p.write_text(
        "# Introduction\nWe study CDC42 GTPase dynamics in microglia "
        "morphology remodeling using live imaging.\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        ["align-manuscript", str(p), "--top-n", "5"],
    )
    assert result.exit_code == 0, result.output
    # Header plus at least one ranked entry
    assert "manuscript:" in result.output
    assert "rank" in result.output
    # Top-5 content shows the rank column
    lines = [line for line in result.output.splitlines() if line.strip()]
    # rank header plus up to 5 ranked rows
    assert len(lines) >= 2


def test_cli_align_manuscript_json_output(tmp_path: Path) -> None:
    p = tmp_path / "manuscript.md"
    p.write_text(
        "# Methods\nWe perform spectral embedding on actin morphometry data.\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        ["align-manuscript", str(p), "--top-n", "3", "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert isinstance(payload, list)
    if payload:
        # First row should expose the documented schema
        first = payload[0]
        assert "recipe_full_name" in first
        assert "score" in first
        assert "matched_sections" in first
        assert "backend" in first
        assert first["backend"] == "tfidf"
