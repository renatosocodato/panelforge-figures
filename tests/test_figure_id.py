"""Tests for the canonical figure-id helper + its adoption (deep-dive #12/#13).

Covers:

A. :func:`normalise_figure_id` — every surface form of a numbered figure id
   normalises to one canonical token; mnemonic ids stay meaningful; edge
   cases (empty, prefix-only, ``Fig.`` abbreviation) are handled.
B. ``xref_linter`` cross-reference matching is now case/format-insensitive:
   a ``\\ref{fig:1A}`` matching a ``\\label{fig:1a}`` was flagged as
   ref_without_block + block_without_ref on the old case-sensitive code and
   is clean now.
C. ``claim_check`` disk-stem lookup is case/format-insensitive via the same
   helper.
D. Deep-dive #13 — the ``correlation_threshold`` default was raised from the
   too-lax ``0.1`` (1% of variance) to the conventional moderate floor
   ``0.3`` (~9% of variance): an ``|r| = 0.2`` correlation that the OLD
   default marked SUPPORTED is now UNSUPPORTED.
"""

from __future__ import annotations

import json
from pathlib import Path

from panelforge_figures.manifest import xref_linter
from panelforge_figures.manifest._figure_id import normalise_figure_id
from panelforge_figures.manifest.claim_check import (
    Claim,
    ClaimAssertion,
    ClaimVerdict,
    FigureEvidence,
    verify_claim,
)

# ───────────────────── A. normalise_figure_id unit tests ─────────────────────


def test_numbered_variants_all_normalise_equal() -> None:
    """Every numbered surface form collapses onto the same canonical token."""
    variants = [
        "Figure 3A",
        "Figure 3a",
        "figure_3a",
        "figure 3a",
        "fig:3a",
        "fig:3A",
        "Fig. 3a",
        "FIG:3A",
    ]
    canonical = {normalise_figure_id(v) for v in variants}
    assert canonical == {"3a"}


def test_plain_numeric_variants_normalise_equal() -> None:
    """A bare number and every prefixed form agree."""
    for v in ("Figure 1", "fig:1", "figure_1", "Fig. 1", "1"):
        assert normalise_figure_id(v) == "1"


def test_mnemonic_ids_keep_meaning() -> None:
    """Author-chosen mnemonic ids drop the prefix but never collapse to ''."""
    assert normalise_figure_id("fig:overview") == "overview"
    assert normalise_figure_id("Fig:Overview") == "overview"
    assert normalise_figure_id("figure_workflow") == "workflow"


def test_edge_cases() -> None:
    """Empty / whitespace → '' ; bare prefix stays non-empty and stable."""
    assert normalise_figure_id("") == ""
    assert normalise_figure_id("   ") == ""
    # A bare prefix must not strip to "" (which would alias every
    # prefix-only id); it stays a stable, non-empty token.
    assert normalise_figure_id("figure") != ""
    assert normalise_figure_id("fig:") != ""


def test_idempotent() -> None:
    """Normalising an already-canonical token is a no-op."""
    for v in ("3a", "1", "overview", "workflow"):
        assert normalise_figure_id(v) == v


# ─────────── B. xref_linter cross-reference case/format insensitivity ─────────


_CASE_MISMATCH_LATEX = r"""\documentclass{article}
\begin{document}
See Figure~\ref{fig:1A} for the result.
\begin{figure}
\centering
\includegraphics{fig1.pdf}
\caption{First figure with a properly long caption explaining the
experimental design and quantification clearly.}
\label{fig:1a}
\end{figure}
\end{document}
"""


def _write(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


def test_xref_match_is_case_insensitive_for_subletter(tmp_path: Path) -> None:
    """A ``\\ref{fig:1A}`` must match a ``\\label{fig:1a}`` block.

    On the old case-sensitive code this manuscript emitted a
    ``ref_without_block`` error (``fig:1A`` not found among blocks) AND a
    ``block_without_ref`` warning (``fig:1a`` never referenced). With the
    canonical figure-id helper both sides normalise to ``"1a"`` and the
    manuscript is clean.
    """
    manuscript = _write(tmp_path, "main.tex", _CASE_MISMATCH_LATEX)
    (tmp_path / "fig1.pdf").write_bytes(b"%PDF-stub")
    report = xref_linter.lint_xrefs(manuscript)

    kinds = {f.kind.value for f in report.findings}
    # The two case-sensitivity false positives are gone.
    assert "ref_without_block" not in kinds, report.findings
    assert "block_without_ref" not in kinds, report.findings
    assert report.verdict == "clean", report.findings


def test_xref_duplicate_block_is_case_insensitive(tmp_path: Path) -> None:
    """Two blocks labelled ``fig:1a`` and ``fig:1A`` are flagged as a duplicate.

    The labels differ only in the subletter case, so on the old
    case-sensitive code they were treated as two distinct figures and the
    duplicate-block check stayed silent. Both now normalise to ``"1a"`` and
    the collision is caught.
    """
    body = r"""\documentclass{article}
\begin{document}
See Figure~\ref{fig:1a}.
\begin{figure}
\centering
\includegraphics{fig1.pdf}
\caption{First copy with a sufficiently long caption to pass length
validation easily and clearly.}
\label{fig:1a}
\end{figure}
\begin{figure}
\centering
\includegraphics{fig1_alt.pdf}
\caption{Second copy reusing the same label but with different case —
the duplicate check should catch this.}
\label{fig:1A}
\end{figure}
\end{document}
"""
    manuscript = _write(tmp_path, "main.tex", body)
    (tmp_path / "fig1.pdf").write_bytes(b"%PDF-stub")
    (tmp_path / "fig1_alt.pdf").write_bytes(b"%PDF-stub")
    report = xref_linter.lint_xrefs(manuscript)
    dup = [f for f in report.findings if f.kind.value == "duplicate_block"]
    assert len(dup) == 1, report.findings
    assert dup[0].severity.value == "error"


# ─────────── C. claim_check disk-stem lookup case/format insensitivity ───────


def _write_provenance(figures_dir: Path, fig_stem: str, audit: dict) -> None:
    fig_path = figures_dir / f"{fig_stem}.png"
    fig_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    sidecar = figures_dir / f"{fig_stem}.png.provenance.json"
    sidecar.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "figure_path": str(fig_path),
                "figure_sha256": "deadbeef",
                "recipe": {"full_name": "test.fake"},
                "data": {"sources": [], "column_mapping": {}},
                "audit": audit,
                "rendering_environment": {},
            }
        )
    )


def test_claim_check_resolves_uppercase_subletter(tmp_path: Path) -> None:
    """A claim about ``Figure 3A`` resolves to the ``figure_3a`` disk stem.

    ``_figure_id_to_stem`` now routes through the canonical helper, so the
    uppercase subletter in prose still finds the lowercase rendered file.
    """
    from panelforge_figures.manifest.claim_check import _figure_id_to_stem

    assert _figure_id_to_stem("Figure 3A") == "figure_3a"
    assert _figure_id_to_stem("fig:3A") == "figure_3a"
    assert _figure_id_to_stem("FIGURE 3A") == "figure_3a"

    figs = tmp_path / "figures"
    figs.mkdir()
    _write_provenance(figs, "figure_3a", {"p_value": 0.001})

    from panelforge_figures.manifest.claim_check import verify_manuscript

    manuscript = tmp_path / "m.tex"
    # Uppercase subletter in prose; rendered file is lowercase.
    manuscript.write_text(
        "Figure 3A shows group A is significantly higher than group B."
    )
    report = verify_manuscript(manuscript, figs)
    assert report.n_claims == 1
    assert report.n_supported == 1, report


# ─────────── D. deep-dive #13 — correlation_threshold default raised ──────────


def _corr_claim() -> Claim:
    return Claim(
        figure_id="Figure 2",
        sentence="Figure 2 shows that X correlates with Y.",
        assertion=ClaimAssertion.correlation_present,
        direction=None,
        magnitude_qualifier=None,
    )


def test_correlation_default_threshold_is_now_moderate() -> None:
    """``|r| = 0.2`` is UNSUPPORTED under the new default (0.3).

    Under the OLD default of ``0.1`` this same r was SUPPORTED — a 4%-of-
    variance correlation passing the screen. The default was raised to the
    conventional moderate floor (0.3, ~9% variance).
    """
    ev = FigureEvidence(
        figure_path=Path("dummy.png"),
        provenance_path=None,
        audit_findings={"correlation_coefficient": 0.2},
        statistical_contract=None,
    )
    v = verify_claim(_corr_claim(), ev)  # default correlation_threshold
    assert v.verdict == ClaimVerdict.unsupported

    # The OLD lax default of 0.1 still SUPPORTS it — proving the change is
    # the threshold value, not the comparison logic.
    v_old = verify_claim(_corr_claim(), ev, correlation_threshold=0.1)
    assert v_old.verdict == ClaimVerdict.supported


def test_correlation_threshold_remains_overridable() -> None:
    """A caller can still tighten or loosen the threshold explicitly."""
    ev = FigureEvidence(
        figure_path=Path("dummy.png"),
        provenance_path=None,
        audit_findings={"pearson_r": 0.35},
        statistical_contract=None,
    )
    # Above the new default → supported.
    assert verify_claim(_corr_claim(), ev).verdict == ClaimVerdict.supported
    # Override to a stricter floor → unsupported.
    assert (
        verify_claim(_corr_claim(), ev, correlation_threshold=0.5).verdict
        == ClaimVerdict.unsupported
    )
