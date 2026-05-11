"""Tests for the manuscript-figure cross-reference linter (Elevation 13).

Exercises the public surface of
:mod:`panelforge_figures.manifest.xref_linter`:

* :func:`lint_xrefs` against synthetic LaTeX manuscripts with various
  defect patterns (clean, ref-without-block, block-without-ref,
  duplicate blocks, missing/short captions, missing rendered files,
  orphan rendered files).
* :func:`_infer_figure_ids_from_filename` filename-to-id heuristic.
* :class:`LintReport` JSON serialisation.
* :func:`render_lint_report_markdown` formatting.
* CLI integration via Click's runner.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

xref_linter = pytest.importorskip(
    "panelforge_figures.manifest.xref_linter"
)

from panelforge_figures.cli import main  # noqa: E402

# --------------------------------------------------------------------------- #
# Synthetic manuscripts                                                       #
# --------------------------------------------------------------------------- #


_CLEAN_LATEX = r"""\documentclass[11pt]{article}
\usepackage{graphicx}
\begin{document}
\title{Clean Test Manuscript}
\maketitle
\section{Results}
Figure~\ref{fig:1} shows the overview.
\begin{figure}[htbp]
\centering
\includegraphics[width=\textwidth]{fig1.pdf}
\caption{Schematic overview of the experimental design — multi-panel
overview describing protocol, treatment, and readout layers.}
\label{fig:1}
\end{figure}
We also refer to \autoref{fig:2} for the quantitative comparison.
\begin{figure}[htbp]
\centering
\includegraphics[width=\textwidth]{fig2.pdf}
\caption{Quantitative comparison between groups showing significantly
higher response in the treated condition (p < 0.001).}
\label{fig:2}
\end{figure}
\end{document}
"""


_REF_WITHOUT_BLOCK_LATEX = r"""\documentclass{article}
\begin{document}
See Figure~\ref{fig:1} and also Figure~\ref{fig:3}.
\begin{figure}
\centering
\includegraphics{fig1.pdf}
\caption{This is the first figure with a sufficiently long caption to
pass the short-caption check.}
\label{fig:1}
\end{figure}
\end{document}
"""


_BLOCK_WITHOUT_REF_LATEX = r"""\documentclass{article}
\begin{document}
See Figure~\ref{fig:1} for the result.
\begin{figure}
\centering
\includegraphics{fig1.pdf}
\caption{First figure with a nice, properly long caption explaining
the experimental design and quantification.}
\label{fig:1}
\end{figure}
\begin{figure}
\centering
\includegraphics{fig2.pdf}
\caption{Second figure with a similarly long caption that is here only
for completeness — but never referenced in body text.}
\label{fig:2}
\end{figure}
\end{document}
"""


_DUPLICATE_BLOCK_LATEX = r"""\documentclass{article}
\begin{document}
See Figure~\ref{fig:1}.
\begin{figure}
\centering
\includegraphics{fig1.pdf}
\caption{First copy of fig:1 with a sufficiently long caption to pass
length validation easily.}
\label{fig:1}
\end{figure}
\begin{figure}
\centering
\includegraphics{fig1_alt.pdf}
\caption{Second copy reusing the same label by mistake — duplicate
block check should catch this.}
\label{fig:1}
\end{figure}
\end{document}
"""


_CAPTION_MISSING_LATEX = r"""\documentclass{article}
\begin{document}
See Figure~\ref{fig:1}.
\begin{figure}
\centering
\includegraphics{fig1.pdf}
\label{fig:1}
\end{figure}
\end{document}
"""


_CAPTION_TOO_SHORT_LATEX = r"""\documentclass{article}
\begin{document}
See Figure~\ref{fig:1}.
\begin{figure}
\centering
\includegraphics{fig1.pdf}
\caption{Short.}
\label{fig:1}
\end{figure}
\end{document}
"""


_RENDERED_FILE_MISSING_LATEX = r"""\documentclass{article}
\begin{document}
See Figure~\ref{fig:1}.
\begin{figure}
\centering
\includegraphics{nonexistent_figure.pdf}
\caption{This figure points at a path that does not exist on disk; the
linter should catch this prior to PDF compilation.}
\label{fig:1}
\end{figure}
\end{document}
"""


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


def _write_manuscript(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


def _write_figures(tmp_path: Path, *names: str) -> Path:
    """Create a ``figures/`` subdir with the listed (empty) files."""
    figures_dir = tmp_path / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    for n in names:
        (figures_dir / n).write_bytes(b"%PDF-stub\n")
    return figures_dir


# --------------------------------------------------------------------------- #
# 1. Clean manuscript — no findings                                            #
# --------------------------------------------------------------------------- #


def test_lint_clean_manuscript_no_findings(tmp_path: Path) -> None:
    """A perfectly cross-referenced manuscript with rendered files must
    return a clean verdict with no findings."""
    manuscript = _write_manuscript(tmp_path, "main.tex", _CLEAN_LATEX)
    # Provide the rendered files \includegraphics points at.
    (tmp_path / "fig1.pdf").write_bytes(b"%PDF-stub")
    (tmp_path / "fig2.pdf").write_bytes(b"%PDF-stub")
    report = xref_linter.lint_xrefs(manuscript)
    assert report.verdict == "clean", report.findings
    assert report.n_errors == 0
    assert report.n_warnings == 0
    assert len(report.findings) == 0
    assert report.n_referenced >= 2
    assert report.n_blocks == 2


# --------------------------------------------------------------------------- #
# 2. ref_without_block                                                         #
# --------------------------------------------------------------------------- #


def test_lint_detects_ref_without_block(tmp_path: Path) -> None:
    """\\ref{fig:3} with no matching block must emit ref_without_block."""
    manuscript = _write_manuscript(tmp_path, "main.tex", _REF_WITHOUT_BLOCK_LATEX)
    (tmp_path / "fig1.pdf").write_bytes(b"%PDF-stub")
    report = xref_linter.lint_xrefs(manuscript)
    kinds = {f.kind.value for f in report.findings}
    assert "ref_without_block" in kinds
    assert report.verdict == "errors"
    ref_findings = [
        f for f in report.findings if f.kind.value == "ref_without_block"
    ]
    assert any(f.figure_id == "fig:3" for f in ref_findings)
    assert all(f.severity.value == "error" for f in ref_findings)


# --------------------------------------------------------------------------- #
# 3. block_without_ref                                                         #
# --------------------------------------------------------------------------- #


def test_lint_detects_block_without_ref(tmp_path: Path) -> None:
    """A figure block whose label is never \\ref-ed must warn."""
    manuscript = _write_manuscript(tmp_path, "main.tex", _BLOCK_WITHOUT_REF_LATEX)
    (tmp_path / "fig1.pdf").write_bytes(b"%PDF-stub")
    (tmp_path / "fig2.pdf").write_bytes(b"%PDF-stub")
    report = xref_linter.lint_xrefs(manuscript)
    block_findings = [
        f for f in report.findings if f.kind.value == "block_without_ref"
    ]
    assert any(f.figure_id == "fig:2" for f in block_findings), report.findings
    # block_without_ref is a warning, not an error.
    assert all(f.severity.value == "warning" for f in block_findings)


# --------------------------------------------------------------------------- #
# 4. duplicate_block                                                           #
# --------------------------------------------------------------------------- #


def test_lint_detects_duplicate_block(tmp_path: Path) -> None:
    """Two figure blocks with the same \\label must be flagged."""
    manuscript = _write_manuscript(tmp_path, "main.tex", _DUPLICATE_BLOCK_LATEX)
    (tmp_path / "fig1.pdf").write_bytes(b"%PDF-stub")
    (tmp_path / "fig1_alt.pdf").write_bytes(b"%PDF-stub")
    report = xref_linter.lint_xrefs(manuscript)
    dup_findings = [
        f for f in report.findings if f.kind.value == "duplicate_block"
    ]
    assert len(dup_findings) == 1
    assert dup_findings[0].figure_id == "fig:1"
    assert dup_findings[0].severity.value == "error"
    assert report.verdict == "errors"


# --------------------------------------------------------------------------- #
# 5. caption_missing                                                           #
# --------------------------------------------------------------------------- #


def test_lint_detects_caption_missing(tmp_path: Path) -> None:
    """A figure block with no \\caption{...} must error."""
    manuscript = _write_manuscript(tmp_path, "main.tex", _CAPTION_MISSING_LATEX)
    (tmp_path / "fig1.pdf").write_bytes(b"%PDF-stub")
    report = xref_linter.lint_xrefs(manuscript)
    cap_findings = [
        f for f in report.findings if f.kind.value == "caption_missing"
    ]
    assert len(cap_findings) >= 1
    assert all(f.severity.value == "error" for f in cap_findings)
    assert cap_findings[0].figure_id == "fig:1"


# --------------------------------------------------------------------------- #
# 6. caption_too_short                                                         #
# --------------------------------------------------------------------------- #


def test_lint_detects_caption_too_short(tmp_path: Path) -> None:
    """A figure with a short caption must warn at the default threshold."""
    manuscript = _write_manuscript(tmp_path, "main.tex", _CAPTION_TOO_SHORT_LATEX)
    (tmp_path / "fig1.pdf").write_bytes(b"%PDF-stub")
    report = xref_linter.lint_xrefs(manuscript, min_caption_chars=30)
    short_findings = [
        f for f in report.findings if f.kind.value == "caption_too_short"
    ]
    assert len(short_findings) == 1
    assert short_findings[0].figure_id == "fig:1"
    assert short_findings[0].severity.value == "warning"


def test_lint_caption_threshold_respected(tmp_path: Path) -> None:
    """Lowering min_caption_chars below caption length suppresses the warning."""
    manuscript = _write_manuscript(tmp_path, "main.tex", _CAPTION_TOO_SHORT_LATEX)
    (tmp_path / "fig1.pdf").write_bytes(b"%PDF-stub")
    report = xref_linter.lint_xrefs(manuscript, min_caption_chars=3)
    short_findings = [
        f for f in report.findings if f.kind.value == "caption_too_short"
    ]
    assert len(short_findings) == 0


# --------------------------------------------------------------------------- #
# 7. rendered_file_missing                                                     #
# --------------------------------------------------------------------------- #


def test_lint_detects_rendered_file_missing(tmp_path: Path) -> None:
    """\\includegraphics path pointing at a non-existent file must error."""
    manuscript = _write_manuscript(
        tmp_path, "main.tex", _RENDERED_FILE_MISSING_LATEX,
    )
    report = xref_linter.lint_xrefs(manuscript)
    missing = [
        f for f in report.findings if f.kind.value == "rendered_file_missing"
    ]
    assert len(missing) == 1
    assert missing[0].severity.value == "error"
    assert "nonexistent_figure.pdf" in missing[0].message


# --------------------------------------------------------------------------- #
# 8. orphan_figure                                                             #
# --------------------------------------------------------------------------- #


def test_lint_detects_orphan_figure(tmp_path: Path) -> None:
    """A rendered file under figures_dir not referenced anywhere → warning."""
    manuscript = _write_manuscript(tmp_path, "main.tex", _CLEAN_LATEX)
    (tmp_path / "fig1.pdf").write_bytes(b"%PDF-stub")
    (tmp_path / "fig2.pdf").write_bytes(b"%PDF-stub")
    figures_dir = _write_figures(tmp_path, "figure_99.pdf")
    report = xref_linter.lint_xrefs(manuscript, figures_dir=figures_dir)
    orphan_findings = [
        f for f in report.findings if f.kind.value == "orphan_figure"
    ]
    assert len(orphan_findings) == 1
    assert orphan_findings[0].severity.value == "warning"
    assert orphan_findings[0].figure_id == "figure_99"


def test_lint_orphan_figure_skipped_when_no_figures_dir(tmp_path: Path) -> None:
    """No figures_dir passed (or non-existent) → orphan check is skipped."""
    manuscript = _write_manuscript(tmp_path, "main.tex", _CLEAN_LATEX)
    (tmp_path / "fig1.pdf").write_bytes(b"%PDF-stub")
    (tmp_path / "fig2.pdf").write_bytes(b"%PDF-stub")
    # Pass a path that doesn't exist.
    report = xref_linter.lint_xrefs(
        manuscript, figures_dir=tmp_path / "does_not_exist",
    )
    assert not any(
        f.kind.value == "orphan_figure" for f in report.findings
    )
    assert report.n_rendered == 0


def test_lint_orphan_figure_skipped_when_used_by_includegraphics(
    tmp_path: Path,
) -> None:
    """A rendered file actually used by \\includegraphics shouldn't orphan-flag."""
    # Manuscript points includegraphics at figures/fig1.pdf inside the
    # figures_dir; the orphan check must recognise it as referenced.
    manuscript_body = r"""\documentclass{article}
\begin{document}
See Figure~\ref{fig:overview}.
\begin{figure}
\centering
\includegraphics{figures/figure_1.pdf}
\caption{Long enough caption to clear the threshold without too much
trouble and prove the orphan-vs-included distinction.}
\label{fig:overview}
\end{figure}
\end{document}
"""
    manuscript = _write_manuscript(tmp_path, "main.tex", manuscript_body)
    figures_dir = _write_figures(tmp_path, "figure_1.pdf")
    report = xref_linter.lint_xrefs(manuscript, figures_dir=figures_dir)
    orphan_findings = [
        f for f in report.findings if f.kind.value == "orphan_figure"
    ]
    assert len(orphan_findings) == 0, report.findings


# --------------------------------------------------------------------------- #
# 9-10. _infer_figure_ids_from_filename                                        #
# --------------------------------------------------------------------------- #


def test_infer_ids_from_simple_figure_filename() -> None:
    """'figure_1' should yield ('fig:1', 'figure_1', 'figure:1', '1')."""
    ids = xref_linter._infer_figure_ids_from_filename("figure_1")
    assert "fig:1" in ids
    assert "figure_1" in ids
    assert "figure:1" in ids
    assert "1" in ids


def test_infer_ids_from_subpanel_filename() -> None:
    """'figure_3b' should yield variants with the 3b suffix."""
    ids = xref_linter._infer_figure_ids_from_filename("figure_3b")
    assert "fig:3b" in ids
    assert "figure_3b" in ids


def test_infer_ids_from_panel_dash_variant() -> None:
    """'panel-2-a' / 'panel_2_a' → ('fig:2a', ...)."""
    ids_dash = xref_linter._infer_figure_ids_from_filename("panel-2-a")
    ids_under = xref_linter._infer_figure_ids_from_filename("panel_2_a")
    assert "fig:2a" in ids_dash
    assert "fig:2a" in ids_under


def test_infer_ids_from_fig_short_form() -> None:
    """'fig_2' → ('fig:2', 'figure_2', 'figure:2', '2')."""
    ids = xref_linter._infer_figure_ids_from_filename("fig_2")
    assert "fig:2" in ids
    assert "2" in ids


def test_infer_ids_fallback_on_unparseable_stem() -> None:
    """A stem that doesn't match the pattern returns just (stem,)."""
    ids = xref_linter._infer_figure_ids_from_filename("overview_diagram")
    assert ids == ("overview_diagram",)


# --------------------------------------------------------------------------- #
# 11. LintReport.to_dict                                                       #
# --------------------------------------------------------------------------- #


def test_lint_report_to_dict_round_trip(tmp_path: Path) -> None:
    """to_dict() output must be JSON-serialisable and round-trip-safe."""
    manuscript = _write_manuscript(tmp_path, "main.tex", _CLEAN_LATEX)
    (tmp_path / "fig1.pdf").write_bytes(b"%PDF-stub")
    (tmp_path / "fig2.pdf").write_bytes(b"%PDF-stub")
    report = xref_linter.lint_xrefs(manuscript)
    d = report.to_dict()
    # All scalar fields are present and JSON-safe.
    encoded = json.dumps(d, default=str)
    assert "verdict" in d
    assert d["verdict"] == report.verdict
    assert d["n_errors"] == report.n_errors
    # Round-trip JSON parse.
    parsed = json.loads(encoded)
    assert parsed["verdict"] == report.verdict


def test_lint_finding_to_dict_serialises_paths(tmp_path: Path) -> None:
    """LintFinding.to_dict serialises file_path as a string."""
    manuscript = _write_manuscript(
        tmp_path, "main.tex", _RENDERED_FILE_MISSING_LATEX,
    )
    report = xref_linter.lint_xrefs(manuscript)
    findings_d = [f.to_dict() for f in report.findings]
    missing = [
        f for f in findings_d if f["kind"] == "rendered_file_missing"
    ]
    assert missing
    # file_path must be a string (or None).
    assert isinstance(missing[0]["file_path"], (str, type(None)))


# --------------------------------------------------------------------------- #
# 12. render_lint_report_markdown                                              #
# --------------------------------------------------------------------------- #


def test_render_lint_report_markdown_header_and_findings(tmp_path: Path) -> None:
    """The markdown renderer should include manuscript path + per-severity sections."""
    manuscript = _write_manuscript(
        tmp_path, "main.tex", _BLOCK_WITHOUT_REF_LATEX,
    )
    (tmp_path / "fig1.pdf").write_bytes(b"%PDF-stub")
    (tmp_path / "fig2.pdf").write_bytes(b"%PDF-stub")
    report = xref_linter.lint_xrefs(manuscript)
    md = xref_linter.render_lint_report_markdown(report)
    assert "# Cross-reference Lint Report" in md
    assert "Manuscript" in md
    assert "Verdict" in md
    if report.n_warnings:
        assert "## Warnings" in md


def test_render_lint_report_markdown_clean_message(tmp_path: Path) -> None:
    """A clean manuscript's markdown should explicitly state no findings."""
    manuscript = _write_manuscript(tmp_path, "main.tex", _CLEAN_LATEX)
    (tmp_path / "fig1.pdf").write_bytes(b"%PDF-stub")
    (tmp_path / "fig2.pdf").write_bytes(b"%PDF-stub")
    report = xref_linter.lint_xrefs(manuscript)
    md = xref_linter.render_lint_report_markdown(report)
    assert "No findings" in md


# --------------------------------------------------------------------------- #
# 13-16. CLI integration                                                       #
# --------------------------------------------------------------------------- #


def test_cli_lint_xrefs_help() -> None:
    """`figures lint xrefs --help` must exit 0."""
    r = CliRunner().invoke(main, ["lint", "xrefs", "--help"])
    assert r.exit_code == 0, r.output
    assert "Usage:" in r.output
    assert "xrefs" in r.output


def test_cli_lint_group_help() -> None:
    """`figures lint --help` must exit 0 and mention xrefs."""
    r = CliRunner().invoke(main, ["lint", "--help"])
    assert r.exit_code == 0, r.output
    assert "xrefs" in r.output


def test_cli_lint_xrefs_clean_exits_zero(tmp_path: Path) -> None:
    """A clean manuscript → CLI exits 0."""
    manuscript = _write_manuscript(tmp_path, "main.tex", _CLEAN_LATEX)
    (tmp_path / "fig1.pdf").write_bytes(b"%PDF-stub")
    (tmp_path / "fig2.pdf").write_bytes(b"%PDF-stub")
    r = CliRunner().invoke(
        main,
        ["lint", "xrefs", str(manuscript), "--figures", str(tmp_path / "missing_dir")],
    )
    assert r.exit_code == 0, r.output
    assert "clean" in r.output


def test_cli_lint_xrefs_errors_exits_one(tmp_path: Path) -> None:
    """A manuscript with errors → CLI exits 1."""
    manuscript = _write_manuscript(
        tmp_path, "main.tex", _REF_WITHOUT_BLOCK_LATEX,
    )
    (tmp_path / "fig1.pdf").write_bytes(b"%PDF-stub")
    r = CliRunner().invoke(
        main,
        ["lint", "xrefs", str(manuscript), "--figures", str(tmp_path / "missing_dir")],
    )
    assert r.exit_code == 1, r.output
    assert "errors" in r.output


def test_cli_lint_xrefs_fail_on_warning(tmp_path: Path) -> None:
    """With --fail-on-warning, a warning-only manuscript exits 1."""
    manuscript = _write_manuscript(
        tmp_path, "main.tex", _BLOCK_WITHOUT_REF_LATEX,
    )
    (tmp_path / "fig1.pdf").write_bytes(b"%PDF-stub")
    (tmp_path / "fig2.pdf").write_bytes(b"%PDF-stub")
    # Without --fail-on-warning the same input should exit 0.
    r_default = CliRunner().invoke(
        main,
        ["lint", "xrefs", str(manuscript), "--figures", str(tmp_path / "missing_dir")],
    )
    assert r_default.exit_code == 0, r_default.output
    r_strict = CliRunner().invoke(
        main,
        [
            "lint", "xrefs", str(manuscript),
            "--figures", str(tmp_path / "missing_dir"),
            "--fail-on-warning",
        ],
    )
    assert r_strict.exit_code == 1, r_strict.output


def test_cli_lint_xrefs_json_output(tmp_path: Path) -> None:
    """--json produces machine-parseable output."""
    manuscript = _write_manuscript(tmp_path, "main.tex", _CLEAN_LATEX)
    (tmp_path / "fig1.pdf").write_bytes(b"%PDF-stub")
    (tmp_path / "fig2.pdf").write_bytes(b"%PDF-stub")
    r = CliRunner().invoke(
        main,
        [
            "lint", "xrefs", str(manuscript),
            "--figures", str(tmp_path / "missing_dir"),
            "--json",
        ],
    )
    assert r.exit_code == 0, r.output
    payload = json.loads(r.output)
    assert payload["verdict"] == "clean"
    assert "findings" in payload


def test_cli_lint_xrefs_output_file(tmp_path: Path) -> None:
    """--output writes the report to the named file and prints a confirmation."""
    manuscript = _write_manuscript(tmp_path, "main.tex", _CLEAN_LATEX)
    (tmp_path / "fig1.pdf").write_bytes(b"%PDF-stub")
    (tmp_path / "fig2.pdf").write_bytes(b"%PDF-stub")
    out_path = tmp_path / "lint_report.md"
    r = CliRunner().invoke(
        main,
        [
            "lint", "xrefs", str(manuscript),
            "--figures", str(tmp_path / "missing_dir"),
            "--output", str(out_path),
        ],
    )
    assert r.exit_code == 0, r.output
    assert out_path.exists()
    content = out_path.read_text(encoding="utf-8")
    assert "Cross-reference Lint Report" in content
