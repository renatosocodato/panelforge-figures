"""Tests for the manuscript-parse module (Elevation 10 — phase 1).

Owned by Build-A; this test suite is authored by Build-C against the
public API documented in the swarm spec.  The whole file is
``importorskip``-gated on :mod:`panelforge_figures.manifest.manuscript_parse`
so the suite at least *parses* during a Build-C-only verification pass
and runs end-to-end once Build-A lands its module.

Public API exercised here (all from ``manuscript_parse``):

* :class:`ExistingManuscript` with ``.format``, ``.figure_blocks``,
  ``.figure_refs``, ``.bibliography_keys``, ``.claims``, ``.venue_hint``,
  ``.referenced_but_undefined``, ``.defined_but_unreferenced``.
* :class:`FigureBlock` (``figure_id``, ``caption_text``, ``label``,
  ``start_line``, ``end_line``).
* :class:`Claim` (``text``, ``figure_id``, ``claim_kind``).
* :class:`ManuscriptFormat` enum (``latex`` / ``markdown``).
* :func:`parse_manuscript` — top-level parser.
* :func:`detect_format` — extension + content sniffer.
* :func:`extract_figure_refs` — \\ref / \\Cref / \\autoref / Markdown.
* :func:`extract_figure_blocks` — ``\\begin{figure}...\\end{figure}`` etc.
* :func:`extract_claims` — natural-language assertions tied to figures.
* :func:`extract_bibliography_keys` — \\cite{...} / [@cite] keys.
* :func:`detect_venue_from_documentclass` — guess venue from docclass.
"""

from __future__ import annotations

from pathlib import Path

import pytest

manuscript_parse = pytest.importorskip(
    "panelforge_figures.manifest.manuscript_parse"
)


# ─────────────────────────── synthetic manuscripts ──────────────────────


_MINIMAL_LATEX = r"""\documentclass[11pt]{article}
\usepackage{graphicx}
\begin{document}
\title{Minimal Test Manuscript}
\maketitle
\section{Results}
Figure~\ref{fig:1} shows the main result.
\begin{figure}[htbp]
\centering
\includegraphics[width=\textwidth]{fig1.pdf}
\caption{Schematic overview of the experimental design.}
\label{fig:1}
\end{figure}
We refer the reader to \autoref{fig:2} for the comparison.
\begin{figure}[htbp]
\centering
\includegraphics[width=\textwidth]{fig2.pdf}
\caption{Quantitative comparison between groups showing significantly
higher response in the treated condition (p~<~0.001) \cite{Smith2020,Doe2021}.}
\label{fig:2}
\end{figure}
See also \Cref{fig:3} for follow-up data \citep{Brown2019}.
\bibliographystyle{plain}
\bibliography{references}
\end{document}
"""

_MINIMAL_MARKDOWN = """# Minimal Markdown Manuscript

## Results

Figure 1 shows the main result.

![Figure 1](figures/fig1.pdf)

**Figure 1.** Schematic overview of the experimental design [@Smith2020].

We refer the reader to Figure 2 for the comparison.

![Figure 2](figures/fig2.pdf)

**Figure 2.** Quantitative comparison between groups showing
significantly higher response in the treated condition [@Doe2021;@Brown2019].

See also Figure 3 for follow-up data.
"""


def _write(tmp: Path, name: str, body: str) -> Path:
    p = tmp / name
    p.write_text(body, encoding="utf-8")
    return p


# ─────────────────────────── parse_manuscript ───────────────────────────


def test_parse_manuscript_minimal_latex_format(tmp_path: Path) -> None:
    """LaTeX manuscript should parse with ``format=ManuscriptFormat.latex``."""
    p = _write(tmp_path, "main.tex", _MINIMAL_LATEX)
    existing = manuscript_parse.parse_manuscript(p)
    fmt = getattr(existing, "format", None)
    assert fmt is not None
    val = getattr(fmt, "value", None) or str(fmt)
    assert val == "latex"


def test_parse_manuscript_minimal_markdown_format(tmp_path: Path) -> None:
    """Markdown manuscript should parse with ``format=ManuscriptFormat.markdown``."""
    p = _write(tmp_path, "main.md", _MINIMAL_MARKDOWN)
    existing = manuscript_parse.parse_manuscript(p)
    fmt = getattr(existing, "format", None)
    val = getattr(fmt, "value", None) or str(fmt)
    assert val == "markdown"


# ─────────────────────────── detect_format ──────────────────────────────


def test_detect_format_tex_extension(tmp_path: Path) -> None:
    """``.tex`` extension → LaTeX format."""
    p = _write(tmp_path, "x.tex", _MINIMAL_LATEX)
    fmt = manuscript_parse.detect_format(p)
    val = getattr(fmt, "value", None) or str(fmt)
    assert val == "latex"


def test_detect_format_md_extension(tmp_path: Path) -> None:
    """``.md`` extension → Markdown format."""
    p = _write(tmp_path, "x.md", _MINIMAL_MARKDOWN)
    fmt = manuscript_parse.detect_format(p)
    val = getattr(fmt, "value", None) or str(fmt)
    assert val == "markdown"


def test_detect_format_txt_latex_content(tmp_path: Path) -> None:
    """``.txt`` with LaTeX-flavoured content should sniff to LaTeX."""
    p = _write(tmp_path, "x.txt", _MINIMAL_LATEX)
    fmt = manuscript_parse.detect_format(p)
    val = getattr(fmt, "value", None) or str(fmt)
    assert val == "latex"


def test_detect_format_txt_markdown_content(tmp_path: Path) -> None:
    """``.txt`` with Markdown-flavoured content should sniff to Markdown."""
    p = _write(tmp_path, "x.txt", _MINIMAL_MARKDOWN)
    fmt = manuscript_parse.detect_format(p)
    val = getattr(fmt, "value", None) or str(fmt)
    assert val == "markdown"


# ─────────────────────────── extract_figure_refs ────────────────────────


def test_extract_figure_refs_latex_finds_ref_cref_autoref() -> None:
    """``\\ref{fig:1}``, ``\\Cref{fig:2}``, ``\\autoref{fig:3}`` should all be found."""
    text = (
        r"See \ref{fig:1} and \Cref{fig:2} and also \autoref{fig:3}."
    )
    refs = manuscript_parse.extract_figure_refs(
        text, manuscript_parse.ManuscriptFormat.latex,
    )
    label_set = {r.figure_id for r in refs}
    assert {"fig:1", "fig:2", "fig:3"}.issubset(label_set)


def test_extract_figure_refs_markdown_finds_figure_n() -> None:
    """Markdown should pick up "Figure 1" / "Figure 2" patterns."""
    text = "Figure 1 shows that. See Figure 2 for context. Figure 3 confirms."
    refs = manuscript_parse.extract_figure_refs(
        text, manuscript_parse.ManuscriptFormat.markdown,
    )
    labels = {r.figure_id for r in refs}
    # Markdown refs are normalised to ``fig:N`` form.
    assert any(
        any(token in label for token in ("fig:1", "fig:2", "fig:3"))
        for label in labels
    ), f"expected fig:N tokens in {labels}"


# ─────────────────────────── extract_figure_blocks ──────────────────────


def test_extract_figure_blocks_finds_two_blocks_latex() -> None:
    """``\\begin{figure}...\\end{figure}`` ×2 → 2 blocks."""
    blocks = manuscript_parse.extract_figure_blocks(
        _MINIMAL_LATEX, manuscript_parse.ManuscriptFormat.latex,
    )
    assert len(blocks) == 2


def test_extract_figure_blocks_captures_single_line_caption() -> None:
    """A single-line ``\\caption{...}`` must populate ``caption_text``."""
    blocks = manuscript_parse.extract_figure_blocks(
        _MINIMAL_LATEX, manuscript_parse.ManuscriptFormat.latex,
    )
    captions = [b.caption_text for b in blocks]
    assert any(
        c and "Schematic overview" in c
        for c in captions
    )


def test_extract_figure_blocks_captures_multi_line_caption() -> None:
    """A multi-line ``\\caption{...}`` must be captured as one string."""
    body = r"""\documentclass{article}
\begin{document}
\begin{figure}
\caption{This caption is split across
multiple lines and includes \emph{italics} and citations \cite{X}.
The end.}
\label{fig:multi}
\end{figure}
\end{document}
"""
    blocks = manuscript_parse.extract_figure_blocks(
        body, manuscript_parse.ManuscriptFormat.latex,
    )
    assert len(blocks) >= 1
    caption = blocks[0].caption_text
    assert caption is not None
    assert "multiple lines" in caption


def test_extract_figure_blocks_uses_label_as_figure_id() -> None:
    """``\\label{fig:foo}`` → ``figure_id = 'fig:foo'`` (or contains 'fig:foo')."""
    blocks = manuscript_parse.extract_figure_blocks(
        _MINIMAL_LATEX, manuscript_parse.ManuscriptFormat.latex,
    )
    labels = [b.figure_id for b in blocks]
    assert any(label and "fig:1" in str(label) for label in labels)
    assert any(label and "fig:2" in str(label) for label in labels)


# ─────────────────────────── extract_claims ─────────────────────────────


def test_extract_claims_significant_difference_higher() -> None:
    """"Figure 1 shows significantly higher..." → significant_difference."""
    text = (
        "Figure 1 shows significantly higher mean response in the "
        "treated condition (p<0.001)."
    )
    claims = manuscript_parse.extract_claims(text)
    assert claims, "expected at least one claim"
    kinds = {str(c.assertion.value).lower() for c in claims}
    assert any(
        any(token in k for token in ("significant", "higher", "diff"))
        for k in kinds
    )


def test_extract_claims_no_difference() -> None:
    """"Figure 2 shows no significant difference" → no_difference."""
    text = (
        "Figure 2 shows no significant difference between the two "
        "groups (p=0.83)."
    )
    claims = manuscript_parse.extract_claims(text)
    assert claims, "expected at least one claim"
    kinds = {str(c.assertion.value).lower() for c in claims}
    assert any(
        any(token in k for token in ("no_diff", "no difference", "null", "equivalence"))
        for k in kinds
    )


# ─────────────────────────── extract_bibliography_keys ──────────────────


def test_extract_bibliography_keys_latex_cite_variants() -> None:
    """``\\cite``, ``\\citep``, ``\\citet`` all contribute keys."""
    text = (
        r"\cite{Smith2020,Doe2021} \citep{Brown2019} \citet{Wilson2018} "
        r"\cite{Adams2017}"
    )
    keys = set(manuscript_parse.extract_bibliography_keys(
        text, manuscript_parse.ManuscriptFormat.latex,
    ))
    expected = {"Smith2020", "Doe2021", "Brown2019", "Wilson2018", "Adams2017"}
    assert expected.issubset(keys)


def test_extract_bibliography_keys_markdown_cites() -> None:
    """``[@key]`` should be extracted from Markdown."""
    text = "See [@Smith2020] and [@Doe2021; @Brown2019]."
    keys = set(manuscript_parse.extract_bibliography_keys(
        text, manuscript_parse.ManuscriptFormat.markdown,
    ))
    assert "Smith2020" in keys
    assert "Doe2021" in keys
    assert "Brown2019" in keys


# ─────────────────────────── detect_venue_from_documentclass ────────────


def test_detect_venue_naturemag() -> None:
    """``naturemag`` documentclass → 'nature' venue string."""
    # The function takes the documentclass *value* (without backslash).
    venue = manuscript_parse.detect_venue_from_documentclass("naturemag")
    assert venue == "nature"


def test_detect_venue_cell() -> None:
    """``cell`` documentclass → 'cell' venue string."""
    venue = manuscript_parse.detect_venue_from_documentclass("cell")
    assert venue == "cell"


def test_detect_venue_article_returns_plain() -> None:
    """Default ``article`` documentclass → 'plain' venue string."""
    venue = manuscript_parse.detect_venue_from_documentclass("article")
    assert venue == "plain"


def test_detect_venue_unknown_returns_none() -> None:
    """An unknown documentclass returns None (caller can fall back)."""
    venue = manuscript_parse.detect_venue_from_documentclass("quux_unknown_2026")
    assert venue is None


# ─────────────────────────── ExistingManuscript dual sets ───────────────


def test_referenced_but_undefined_includes_fig3(tmp_path: Path) -> None:
    """Refs to fig:3 with no matching block → returns ('fig:3',)."""
    p = _write(tmp_path, "x.tex", _MINIMAL_LATEX)
    existing = manuscript_parse.parse_manuscript(p)
    missing = existing.referenced_but_undefined
    labels = set(missing)
    assert any("fig:3" in label for label in labels), (
        f"expected 'fig:3' in referenced_but_undefined; got {labels}"
    )


def test_defined_but_unreferenced_finds_orphan(tmp_path: Path) -> None:
    """A figure defined but never referenced → flagged."""
    text = r"""\documentclass{article}
\begin{document}
See \ref{fig:1} only.
\begin{figure}\caption{One.}\label{fig:1}\end{figure}
\begin{figure}\caption{Two — orphan.}\label{fig:2}\end{figure}
\end{document}
"""
    p = _write(tmp_path, "orphan.tex", text)
    existing = manuscript_parse.parse_manuscript(p)
    orphans = set(existing.defined_but_unreferenced)
    assert any("fig:2" in label for label in orphans), (
        f"expected 'fig:2' in defined_but_unreferenced; got {orphans}"
    )


# ─────────────────────────── Markdown caption pattern ───────────────────


def test_parse_markdown_handles_figure_pattern(tmp_path: Path) -> None:
    """Markdown ``![](path)`` followed by ``**Figure N.**`` should yield a block."""
    p = _write(tmp_path, "x.md", _MINIMAL_MARKDOWN)
    existing = manuscript_parse.parse_manuscript(p)
    blocks = getattr(existing, "figure_blocks", None) or ()
    assert len(blocks) >= 2, (
        f"expected ≥2 figure blocks in markdown manuscript; got {len(blocks)}"
    )


def test_parse_markdown_extracts_at_cite_keys(tmp_path: Path) -> None:
    """``[@cite_key]`` references must be extracted."""
    p = _write(tmp_path, "x.md", _MINIMAL_MARKDOWN)
    existing = manuscript_parse.parse_manuscript(p)
    keys = set(getattr(existing, "bibliography_keys_cited", ()) or ())
    assert "Smith2020" in keys
    assert "Doe2021" in keys
    assert "Brown2019" in keys
