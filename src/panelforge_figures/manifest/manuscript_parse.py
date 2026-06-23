"""Manuscript parser — Elevation 10 (blueprint collision handling).

Parses an existing manuscript (``.tex`` or ``.md``) into a structured
:class:`ExistingManuscript` record so the collision detector and the
blueprint-importer can reason about its contents without re-reading the
file.  Parsing is regex-based (no LaTeX AST dependency required); a
small optional enrichment hook is provided that lazily imports
``pylatexenc`` if the caller wants richer caption stripping.

Design notes
------------
* The parser is **best-effort and tolerant** — malformed sections,
  unbalanced braces, and missing ``\\label`` directives degrade
  gracefully into empty fields rather than raising.  The only
  raise-condition is "the file is unreadable" or "the format cannot be
  detected even from a content sniff".
* The parser is **format-aware**: a ``.tex`` file is parsed with
  LaTeX heuristics, a ``.md`` file with Markdown heuristics; files
  with neither extension are content-sniffed against the first 500
  bytes.
* The parser is **read-only** — the input file is opened, read, and
  closed.  No on-disk side-effects.
* The data shapes mirror, where applicable, the existing
  :class:`Claim` / :class:`ClaimAssertion` types in
  :mod:`manifest.claim_check` (E2).  Re-importing those types would
  drag in claim-verification machinery the collision detector does
  not need, so we declare standalone copies and document the parity.

Public API
----------
* :class:`ManuscriptFormat`, :class:`ManuscriptParseError`,
  :class:`ClaimAssertion` — small enums / error class.
* :class:`Section`, :class:`FigureRef`, :class:`FigureBlock`,
  :class:`Claim`, :class:`ExistingManuscript` — frozen dataclasses.
* :func:`detect_format`, :func:`detect_venue_from_documentclass`.
* :func:`extract_sections`, :func:`extract_figure_refs`,
  :func:`extract_figure_blocks`, :func:`extract_claims`,
  :func:`extract_bibliography_keys`.
* :func:`parse_latex`, :func:`parse_markdown`,
  :func:`parse_manuscript` — top-level dispatchers.
* :func:`enrich_with_pylatexenc` — optional best-effort caption
  enrichment that lazily imports ``pylatexenc`` (returns the input
  unchanged if the dependency is absent).

See ``docs/spec_e10_manuscript_collision.md`` §2 for the full spec.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

__all__ = [
    "ManuscriptParseError",
    "ManuscriptFormat",
    "Section",
    "FigureRef",
    "FigureBlock",
    "Claim",
    "ClaimAssertion",
    "ExistingManuscript",
    "parse_manuscript",
    "parse_latex",
    "parse_markdown",
    "detect_format",
    "detect_venue_from_documentclass",
    "extract_figure_refs",
    "extract_figure_blocks",
    "extract_claims",
    "extract_sections",
    "extract_bibliography_keys",
    "enrich_with_pylatexenc",
]


# --------------------------------------------------------------------------- #
# Enums + errors                                                              #
# --------------------------------------------------------------------------- #


class ManuscriptParseError(RuntimeError):
    """Raised on unreadable files or clearly malformed structure.

    The parser tries hard to degrade rather than raise — this exception
    only fires when the input file cannot be opened, or when format
    detection fails for a file with no recognisable extension and no
    LaTeX/Markdown signal in the first 500 bytes.
    """


class ManuscriptFormat(StrEnum):
    """Output of :func:`detect_format`."""

    latex = "latex"
    markdown = "markdown"


class ClaimAssertion(StrEnum):
    """Heuristic classification of a sentence's claim.

    Mirrors :class:`manifest.claim_check.ClaimAssertion` (E2). We
    declare a standalone copy so the collision detector does not need
    to import claim-verification machinery.
    """

    significant_difference = "significant_difference"
    no_difference = "no_difference"
    correlation_present = "correlation_present"
    no_correlation = "no_correlation"
    effect_size_above = "effect_size_above"
    descriptive = "descriptive"
    unparseable = "unparseable"


# --------------------------------------------------------------------------- #
# Dataclasses                                                                 #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Section:
    """A ``\\section`` / ``\\subsection`` (LaTeX) or ``#`` / ``##`` (Markdown).

    ``level`` follows the LaTeX convention (1 = section, 2 = subsection,
    3 = subsubsection); Markdown headings map ``##`` → 1, ``###`` → 2,
    ``####`` → 3 so the two formats compare cleanly.
    """

    name: str
    level: int
    start_line: int       # 1-indexed
    end_line: int         # exclusive
    word_count: int


@dataclass(frozen=True)
class FigureRef:
    """A ``\\ref{fig:N}`` occurrence (LaTeX) or ``Figure N`` mention (markdown)."""

    figure_id: str            # canonical "fig:N" / "fig:3a" identifier
    line_number: int          # 1-indexed
    sentence_excerpt: str     # up to ~200 chars around the reference


@dataclass(frozen=True)
class FigureBlock:
    """A ``\\begin{figure}...\\end{figure}`` block or markdown image+caption.

    ``has_provenance_comment`` flags whether the block contains a
    panelforge-style provenance comment (``<!-- figure sha256: HEX -->``
    in markdown, ``% figure sha256: HEX`` in LaTeX). The collision
    detector uses that flag to distinguish manuscript figures rendered
    by panelforge from hand-authored ones.
    """

    figure_id: str                       # value from \label{fig:...}
    start_line: int                      # 1-indexed
    end_line: int                        # exclusive
    caption_text: str                    # raw caption (braces stripped)
    includegraphics_path: str | None
    has_provenance_comment: bool


@dataclass(frozen=True)
class Claim:
    """A "Figure N shows X" sentence with parsed assertion + direction."""

    figure_id: str
    sentence: str
    assertion: ClaimAssertion
    direction: str | None
    magnitude_qualifier: str | None
    line_number: int


@dataclass(frozen=True)
class ExistingManuscript:
    """Structured snapshot of a manuscript on disk.

    The record is immutable and JSON-serialisable via
    :meth:`to_dict`.  It is consumed by the E10 collision detector
    (Build-B) and by the blueprint-importer (Build-C).
    """

    path: Path
    format: ManuscriptFormat
    venue: str | None
    title: str | None
    n_lines: int
    n_words: int
    sections: tuple[Section, ...]
    figure_refs: tuple[FigureRef, ...]
    figure_blocks: tuple[FigureBlock, ...]
    claims: tuple[Claim, ...]
    bibliography_keys_cited: tuple[str, ...]
    has_methods_section: bool
    has_star_methods: bool
    word_count_by_section: dict[str, int] = field(default_factory=dict)

    @property
    def referenced_but_undefined(self) -> tuple[str, ...]:
        """Figure ids that appear in ``figure_refs`` but not ``figure_blocks``.

        Useful for "broken-cross-reference" diagnostics: the manuscript
        says ``\\ref{fig:5}`` but no ``\\begin{figure}`` block carries
        ``\\label{fig:5}``.
        """
        defined = {b.figure_id for b in self.figure_blocks}
        referenced = {r.figure_id for r in self.figure_refs}
        return tuple(sorted(referenced - defined))

    @property
    def defined_but_unreferenced(self) -> tuple[str, ...]:
        """Figure ids in ``figure_blocks`` but never mentioned in prose.

        Useful for "orphan figure" diagnostics: the manuscript embeds
        a figure but never refers to it in the body text.
        """
        defined = {b.figure_id for b in self.figure_blocks}
        referenced = {r.figure_id for r in self.figure_refs}
        return tuple(sorted(defined - referenced))

    def to_dict(self) -> dict[str, Any]:
        """Render as a JSON-serialisable dict."""
        return {
            "path": str(self.path),
            "format": self.format.value,
            "venue": self.venue,
            "title": self.title,
            "n_lines": self.n_lines,
            "n_words": self.n_words,
            "sections": [
                {
                    "name": s.name,
                    "level": s.level,
                    "start_line": s.start_line,
                    "end_line": s.end_line,
                    "word_count": s.word_count,
                }
                for s in self.sections
            ],
            "figure_refs": [
                {
                    "figure_id": r.figure_id,
                    "line_number": r.line_number,
                    "sentence_excerpt": r.sentence_excerpt,
                }
                for r in self.figure_refs
            ],
            "figure_blocks": [
                {
                    "figure_id": b.figure_id,
                    "start_line": b.start_line,
                    "end_line": b.end_line,
                    "caption_text": b.caption_text,
                    "includegraphics_path": b.includegraphics_path,
                    "has_provenance_comment": b.has_provenance_comment,
                }
                for b in self.figure_blocks
            ],
            "claims": [
                {
                    "figure_id": c.figure_id,
                    "sentence": c.sentence,
                    "assertion": c.assertion.value,
                    "direction": c.direction,
                    "magnitude_qualifier": c.magnitude_qualifier,
                    "line_number": c.line_number,
                }
                for c in self.claims
            ],
            "bibliography_keys_cited": list(self.bibliography_keys_cited),
            "has_methods_section": self.has_methods_section,
            "has_star_methods": self.has_star_methods,
            "word_count_by_section": dict(self.word_count_by_section),
            "referenced_but_undefined": list(self.referenced_but_undefined),
            "defined_but_unreferenced": list(self.defined_but_unreferenced),
        }


# --------------------------------------------------------------------------- #
# Venue detection                                                             #
# --------------------------------------------------------------------------- #


_VENUE_HINTS: dict[str, str] = {
    "naturemag": "nature",
    "nature": "nature",
    "cell": "cell",
    "cellpress": "cell",
    "nejm": "nejm",
    "nejmcc": "nejm",
    "biorxiv": "biorxiv",
    "science": "science",
    "sciencemag": "science",
    "article": "plain",
}


def detect_venue_from_documentclass(documentclass: str) -> str | None:
    """Heuristic lookup: ``\\documentclass{cellpress}`` → ``"cell"``.

    The match is case-insensitive and substring-based: any documentclass
    *containing* a known hint (e.g. ``nature-template``) resolves to
    that venue.  Returns ``None`` when no hint matches — callers
    typically fall back to ``"plain"`` in that case.
    """
    if not documentclass:
        return None
    needle = documentclass.lower().strip()
    # Try exact match first.
    if needle in _VENUE_HINTS:
        return _VENUE_HINTS[needle]
    # Then substring match (longest hint wins so "nejmcc" beats "nejm").
    matches = [
        (hint, venue) for hint, venue in _VENUE_HINTS.items() if hint in needle
    ]
    if not matches:
        return None
    matches.sort(key=lambda pair: len(pair[0]), reverse=True)
    return matches[0][1]


# --------------------------------------------------------------------------- #
# Format detection                                                            #
# --------------------------------------------------------------------------- #


_LATEX_SNIFF = re.compile(r"\\documentclass|\\begin\{document\}|\\section\{")
_MARKDOWN_SNIFF = re.compile(r"^#{1,6}\s+\S|^---\s*$", re.MULTILINE)


def detect_format(path: Path) -> ManuscriptFormat:
    """Decide whether ``path`` is a LaTeX or Markdown manuscript.

    Strategy:

    1. ``.tex`` extension → :attr:`ManuscriptFormat.latex`.
    2. ``.md`` / ``.markdown`` extension → :attr:`ManuscriptFormat.markdown`.
    3. Otherwise, read the first 500 bytes and look for LaTeX commands
       (``\\documentclass``, ``\\begin{document}``, ``\\section{``); if
       found, return latex.
    4. Otherwise, look for Markdown headers or YAML frontmatter; if
       found, return markdown.
    5. Otherwise, raise :class:`ManuscriptParseError`.
    """
    suffix = path.suffix.lower()
    if suffix == ".tex":
        return ManuscriptFormat.latex
    if suffix in {".md", ".markdown"}:
        return ManuscriptFormat.markdown

    try:
        with path.open("rb") as fh:
            sample = fh.read(500).decode("utf-8", errors="replace")
    except OSError as exc:
        raise ManuscriptParseError(
            f"cannot read {path} for format detection: {exc}"
        ) from exc

    if _LATEX_SNIFF.search(sample):
        return ManuscriptFormat.latex
    if _MARKDOWN_SNIFF.search(sample):
        return ManuscriptFormat.markdown
    raise ManuscriptParseError(
        f"cannot detect format of {path}: no .tex/.md extension and "
        f"first 500 bytes contain neither LaTeX nor Markdown signals"
    )


# --------------------------------------------------------------------------- #
# Regex patterns                                                              #
# --------------------------------------------------------------------------- #


# LaTeX patterns
_LATEX_DOCUMENTCLASS = re.compile(
    r"\\documentclass(?:\[[^\]]*\])?\{([^}]+)\}",
)
_LATEX_TITLE = re.compile(r"\\title\{")
_LATEX_SECTION = re.compile(
    r"\\(section|subsection|subsubsection)\*?\{",
)
_LATEX_FIGURE_BEGIN = re.compile(r"\\begin\{figure\*?\}")
_LATEX_FIGURE_END = re.compile(r"\\end\{figure\*?\}")
_LATEX_LABEL = re.compile(r"\\label\{([^}]+)\}")
_LATEX_INCLUDEGRAPHICS = re.compile(
    r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}",
)
_LATEX_CAPTION = re.compile(r"\\caption\{")
_LATEX_CITE = re.compile(
    r"\\(?:cite|citep|citet|citeauthor|citeyear|Cite|Citep|Citet)"
    r"(?:\[[^\]]*\])?(?:\[[^\]]*\])?\{([^}]+)\}",
)
_LATEX_FIGURE_REF = re.compile(
    r"\\(?:ref|Ref|autoref|Autoref|cref|Cref|nameref|eqref|pageref)"
    r"\{(fig:[^}]+)\}",
)
# panelforge provenance breadcrumb (LaTeX: % figure sha256: HEX; Markdown: <!-- ... -->)
_LATEX_PROVENANCE = re.compile(r"%\s*figure\s+sha256\s*:", re.IGNORECASE)
_MARKDOWN_PROVENANCE = re.compile(
    r"<!--\s*figure\s+sha256\s*:[^>]*-->", re.IGNORECASE,
)

# STAR Methods (special-case Cell-style heading)
_STAR_METHODS = re.compile(
    r"STAR\s*(?:\\?\$?\\?star\\?\$?)?\s*Methods", re.IGNORECASE,
)

# Markdown patterns
_MD_HEADER = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_MD_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
# **Figure N.** / **Figure N |** — caption start markers
_MD_CAPTION_START = re.compile(
    r"\*\*(?:Figure|Fig\.?)\s*([0-9A-Za-z\-]+)\s*[.|:][^*]*\*\*",
)
# Pandoc citations: [@key] / [-@key] / [@key1; @key2]
_MD_CITE = re.compile(r"\[(?:-?@[^@\];]+)(?:;\s*-?@[^@\];]+)*\]")
_MD_CITE_INNER = re.compile(r"-?@([A-Za-z0-9_\-:.]+)")
_MD_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_MD_FRONTMATTER_KV = re.compile(r"^([A-Za-z_][A-Za-z0-9_\-]*)\s*:\s*(.+?)\s*$")

# Figure-mention pattern (used in both formats for *prose* references):
# matches "Figure 1", "Fig. 3", "Figure 3a" — captures the id.
_FIGURE_MENTION = re.compile(
    r"\b(?:Figure|Fig\.?)\s*([0-9]+)([a-zA-Z]?)\b",
    re.IGNORECASE,
)


# Claim classification (mirror of claim_check.py — keep in sync).
# Order matters: _NO_DIFFERENCE before _SIGNIFICANT.
_NO_DIFFERENCE_PATTERN = re.compile(
    r"\b(?:no\s+significant|not\s+significant|no\s+difference|"
    r"no\s+effect|null\s+result|n\.s\.)\b",
    re.IGNORECASE,
)
_SIGNIFICANT_PATTERN = re.compile(
    r"\b(?:significantly|p\s*[<≤=]\s*0?\.0\d|highly\s+significant)\b",
    re.IGNORECASE,
)
_NO_CORRELATION_PATTERN = re.compile(
    r"\b(?:uncorrelated|no\s+correlation|no\s+association)\b",
    re.IGNORECASE,
)
_CORRELATION_PATTERN = re.compile(
    r"\b(?:correlat|associat|relationship|cor=)",
    re.IGNORECASE,
)
_DESCRIPTIVE_PATTERN = re.compile(
    r"\b(?:shows|depicts|illustrates|displays|presents|visualizes|"
    r"summarizes|summarises)\b",
    re.IGNORECASE,
)
_EFFECT_SIZE_PATTERN = re.compile(
    r"\b(?:cohen[''']?s?\s*d|effect\s+size|d\s*[=>]\s*0?\.\d+|"
    r"η\s*²|partial\s+eta\s*-?\s*squared)\b",
    re.IGNORECASE,
)
_DIRECTION_HIGHER = re.compile(
    r"\b(?:higher|greater|elevated|increased|larger|more)\b",
    re.IGNORECASE,
)
_DIRECTION_LOWER = re.compile(
    r"\b(?:lower|reduced|decreased|smaller|less)\b",
    re.IGNORECASE,
)
_MAGNITUDE_PATTERN = re.compile(
    r"\b(significantly|substantially|markedly|slightly|weakly|strongly|"
    r"modestly|moderately)\b",
    re.IGNORECASE,
)


# --------------------------------------------------------------------------- #
# Brace-balancing helper                                                      #
# --------------------------------------------------------------------------- #


def _balance_braces(text: str, start: int) -> int:
    """Return the index *just after* the closing ``}`` that balances ``{``.

    ``start`` must point at the opening ``{``. Returns ``-1`` if the
    braces are unbalanced (truncated file). Backslash-escaped braces
    (``\\{`` / ``\\}``) are treated as literal characters and skipped.
    """
    if start >= len(text) or text[start] != "{":
        return -1
    depth = 0
    i = start
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text):
            # Skip escaped char (covers \{, \}, \\, etc.).
            i += 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def _line_number_of(text: str, offset: int) -> int:
    """Convert a 0-based character offset to a 1-based line number."""
    return text.count("\n", 0, offset) + 1


def _word_count(text: str) -> int:
    """Count whitespace-separated tokens in ``text``."""
    return len(text.split())


def _sentence_excerpt(text: str, offset: int, *, window: int = 200) -> str:
    """Return up to ``window`` chars around ``offset`` for context.

    Tries to expand backward/forward to nearest sentence boundary,
    capped at ``window`` chars total. Whitespace is collapsed.
    """
    left = max(0, offset - window // 2)
    right = min(len(text), offset + window // 2)
    # Snap left to a sentence boundary if one exists in the prefix.
    snippet_left = text[left:offset]
    m = re.search(r"[.!?]\s+([^.!?]*)$", snippet_left)
    if m is not None:
        left = left + m.start(1)
    excerpt = text[left:right].strip()
    return re.sub(r"\s+", " ", excerpt)


# --------------------------------------------------------------------------- #
# LaTeX extraction helpers                                                    #
# --------------------------------------------------------------------------- #


def _extract_latex_title(text: str) -> str | None:
    """Return the contents of the first ``\\title{...}`` macro, or ``None``."""
    m = _LATEX_TITLE.search(text)
    if m is None:
        return None
    open_brace = m.end() - 1
    close = _balance_braces(text, open_brace)
    if close < 0:
        return None
    title = text[open_brace + 1 : close - 1].strip()
    # Strip LaTeX line breaks (``\\``) and excess whitespace.
    title = re.sub(r"\\\\\s*", " ", title)
    title = re.sub(r"\s+", " ", title)
    return title or None


def _strip_latex_caption_inner(raw: str) -> str:
    """Collapse a raw caption string into single-line plain-ish text.

    Strips line breaks, collapses whitespace, and removes a handful of
    trivially-removable LaTeX commands without dragging in a full LaTeX
    AST (``\\textbf{...}``, ``\\emph{...}``, ``\\textit{...}``,
    ``\\label{...}``). Anything more elaborate is left verbatim — the
    collision detector treats the caption as opaque prose.
    """
    txt = raw
    txt = _LATEX_LABEL.sub("", txt)
    # Strip simple \textbf / \emph / \textit / \texttt with brace contents.
    txt = re.sub(
        r"\\(?:textbf|emph|textit|texttt|textsf|textsc)\{([^{}]*)\}",
        r"\1",
        txt,
    )
    txt = re.sub(r"\\\\", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def extract_sections(text: str, fmt: ManuscriptFormat) -> tuple[Section, ...]:
    """Return all ``\\section`` / ``##`` headings in document order.

    Levels:

    * LaTeX: ``\\section`` → 1, ``\\subsection`` → 2, ``\\subsubsection`` → 3.
    * Markdown: ``##`` → 1, ``###`` → 2, ``####`` → 3 (``#`` is reserved
      for the document title).

    ``word_count`` covers the body between this heading and the next
    heading (or end-of-document); ``end_line`` is exclusive.
    """
    if fmt == ManuscriptFormat.latex:
        return _extract_latex_sections(text)
    return _extract_markdown_sections(text)


def _extract_latex_sections(text: str) -> tuple[Section, ...]:
    """LaTeX-specific section walker."""
    level_map = {"section": 1, "subsection": 2, "subsubsection": 3}
    found: list[tuple[int, str, int]] = []  # (start_offset, name, level)
    for m in _LATEX_SECTION.finditer(text):
        kind = m.group(1)
        open_brace = m.end() - 1
        close = _balance_braces(text, open_brace)
        if close < 0:
            continue
        name = text[open_brace + 1 : close - 1].strip()
        name = re.sub(r"\s+", " ", name)
        found.append((m.start(), name, level_map[kind]))

    sections: list[Section] = []
    for idx, (start_off, name, level) in enumerate(found):
        start_line = _line_number_of(text, start_off)
        if idx + 1 < len(found):
            end_off = found[idx + 1][0]
        else:
            end_off = len(text)
        end_line = _line_number_of(text, end_off)
        body = text[start_off:end_off]
        sections.append(
            Section(
                name=name,
                level=level,
                start_line=start_line,
                end_line=end_line,
                word_count=_word_count(body),
            )
        )
    return tuple(sections)


def _extract_markdown_sections(text: str) -> tuple[Section, ...]:
    """Markdown-specific section walker (skips the top-level ``#`` title)."""
    lines = text.splitlines()
    found: list[tuple[int, str, int]] = []  # (line_idx_0based, name, level)
    for idx, ln in enumerate(lines):
        m = _MD_HEADER.match(ln)
        if m is None:
            continue
        hashes = m.group(1)
        name = m.group(2).strip()
        depth = len(hashes)
        if depth < 2:
            # Skip the doc title (level-1 `#`).
            continue
        found.append((idx, name, depth - 1))  # ## → 1, ### → 2

    sections: list[Section] = []
    for i, (line_idx, name, level) in enumerate(found):
        start_line = line_idx + 1
        if i + 1 < len(found):
            end_line = found[i + 1][0] + 1
        else:
            end_line = len(lines) + 1
        body_lines = lines[line_idx:end_line - 1]
        body = "\n".join(body_lines)
        sections.append(
            Section(
                name=name,
                level=level,
                start_line=start_line,
                end_line=end_line,
                word_count=_word_count(body),
            )
        )
    return tuple(sections)


# --------------------------------------------------------------------------- #
# Figure-ref extraction                                                       #
# --------------------------------------------------------------------------- #


def extract_figure_refs(text: str, fmt: ManuscriptFormat) -> tuple[FigureRef, ...]:
    """Return every figure cross-reference in document order.

    LaTeX: matches ``\\ref{fig:N}``, ``\\Cref{fig:N}``, ``\\autoref{fig:N}``,
    ``\\eqref{fig:N}``, ``\\pageref{fig:N}``, ``\\nameref{fig:N}``.

    Markdown: matches free-text ``Figure N`` / ``Fig. N`` / ``Fig 3a``;
    the captured id is normalised to ``fig:<n>`` so it sorts with LaTeX
    refs in mixed corpora.
    """
    if fmt == ManuscriptFormat.latex:
        return _extract_latex_figure_refs(text)
    return _extract_markdown_figure_refs(text)


def _extract_latex_figure_refs(text: str) -> tuple[FigureRef, ...]:
    refs: list[FigureRef] = []
    for m in _LATEX_FIGURE_REF.finditer(text):
        fig_id = m.group(1).strip()
        offset = m.start()
        refs.append(
            FigureRef(
                figure_id=fig_id,
                line_number=_line_number_of(text, offset),
                sentence_excerpt=_sentence_excerpt(text, offset),
            )
        )
    return tuple(refs)


def _extract_markdown_figure_refs(text: str) -> tuple[FigureRef, ...]:
    """Markdown figure mentions, normalised to ``fig:N`` form.

    To keep callers' lives easy we *skip* mentions that fall on lines
    matching a markdown image caption (``**Figure N.** ...``) — those
    are handled by :func:`_extract_markdown_figure_blocks` and would
    otherwise produce spurious self-references.
    """
    refs: list[FigureRef] = []
    lines = text.splitlines()
    line_offsets = _build_line_offsets(text)

    # Pre-compute "caption-start" line indices to skip them.
    caption_lines: set[int] = set()
    for idx, ln in enumerate(lines):
        if _MD_CAPTION_START.search(ln):
            caption_lines.add(idx)

    for m in _FIGURE_MENTION.finditer(text):
        n = m.group(1)
        sub = m.group(2) or ""
        offset = m.start()
        line_idx = _line_index_for_offset(line_offsets, offset)
        if line_idx in caption_lines:
            continue
        fig_id = f"fig:{n}{sub.lower()}"
        refs.append(
            FigureRef(
                figure_id=fig_id,
                line_number=line_idx + 1,
                sentence_excerpt=_sentence_excerpt(text, offset),
            )
        )
    return tuple(refs)


def _build_line_offsets(text: str) -> list[int]:
    """Build a list of character offsets where each line starts.

    Used for fast offset → line-index conversion when scanning many
    matches in the same document.
    """
    offsets = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            offsets.append(i + 1)
    return offsets


def _line_index_for_offset(line_offsets: list[int], offset: int) -> int:
    """Binary search ``line_offsets`` for the line containing ``offset``."""
    # bisect_right - 1 gives the start-of-line offset <= offset.
    lo, hi = 0, len(line_offsets)
    while lo < hi:
        mid = (lo + hi) // 2
        if line_offsets[mid] <= offset:
            lo = mid + 1
        else:
            hi = mid
    return max(0, lo - 1)


# --------------------------------------------------------------------------- #
# Figure-block extraction                                                     #
# --------------------------------------------------------------------------- #


def extract_figure_blocks(
    text: str, fmt: ManuscriptFormat,
) -> tuple[FigureBlock, ...]:
    """Return every figure block in document order.

    LaTeX: matches ``\\begin{figure}...\\end{figure}`` (and ``figure*``
    variants); pulls ``\\label``, ``\\includegraphics``, ``\\caption``.

    Markdown: matches an ``![alt](path)`` image immediately followed
    (within ~6 lines) by a ``**Figure N.**`` caption marker.
    """
    if fmt == ManuscriptFormat.latex:
        return _extract_latex_figure_blocks(text)
    return _extract_markdown_figure_blocks(text)


def _extract_latex_figure_blocks(text: str) -> tuple[FigureBlock, ...]:
    blocks: list[FigureBlock] = []
    for begin_match in _LATEX_FIGURE_BEGIN.finditer(text):
        begin_off = begin_match.start()
        end_match = _LATEX_FIGURE_END.search(text, begin_match.end())
        if end_match is None:
            # Truncated/unterminated figure — skip rather than raise.
            continue
        end_off = end_match.end()
        block_text = text[begin_off:end_off]

        # \label{...}
        label_match = _LATEX_LABEL.search(block_text)
        figure_id = label_match.group(1).strip() if label_match else ""

        # \includegraphics{...}
        inc_match = _LATEX_INCLUDEGRAPHICS.search(block_text)
        graphics_path = inc_match.group(1).strip() if inc_match else None

        # \caption{ ... } — brace-balanced (captions can be multi-line).
        cap_match = _LATEX_CAPTION.search(block_text)
        caption_text = ""
        if cap_match is not None:
            cap_open = begin_off + cap_match.end() - 1
            cap_close = _balance_braces(text, cap_open)
            if cap_close > 0:
                caption_text = _strip_latex_caption_inner(
                    text[cap_open + 1 : cap_close - 1]
                )

        # Provenance comment? (LaTeX comments use %; we accept both
        # in-block and a comment line immediately preceding \begin{figure}.)
        has_prov = bool(_LATEX_PROVENANCE.search(block_text))
        if not has_prov:
            # Check up to 3 lines of leading context.
            lead_start = text.rfind("\n", 0, max(0, begin_off - 1))
            lead_window = text[max(0, lead_start - 200) : begin_off]
            has_prov = bool(_LATEX_PROVENANCE.search(lead_window))

        blocks.append(
            FigureBlock(
                figure_id=figure_id,
                start_line=_line_number_of(text, begin_off),
                end_line=_line_number_of(text, end_off) + 1,
                caption_text=caption_text,
                includegraphics_path=graphics_path,
                has_provenance_comment=has_prov,
            )
        )
    return tuple(blocks)


def _extract_markdown_figure_blocks(text: str) -> tuple[FigureBlock, ...]:
    """Markdown figure blocks: image+caption pairs separated by ≤6 blank lines."""
    lines = text.splitlines()
    blocks: list[FigureBlock] = []
    i = 0
    while i < len(lines):
        img_m = _MD_IMAGE.search(lines[i])
        if img_m is None:
            i += 1
            continue
        graphics_path = img_m.group(1).strip()

        # Scan forward up to 6 lines for the caption marker.
        caption_line_idx: int | None = None
        for j in range(i + 1, min(len(lines), i + 7)):
            if _MD_CAPTION_START.search(lines[j]):
                caption_line_idx = j
                break

        if caption_line_idx is None:
            i += 1
            continue

        cap_match = _MD_CAPTION_START.search(lines[caption_line_idx])
        # Defensive: cap_match is guaranteed non-None given the loop above.
        fig_token = cap_match.group(1) if cap_match else ""
        figure_id = f"fig:{fig_token.lower()}"

        # The caption body extends until the next blank line / next image.
        end_idx = caption_line_idx
        while end_idx + 1 < len(lines):
            nxt = lines[end_idx + 1]
            if nxt.strip() == "":
                break
            if _MD_IMAGE.search(nxt):
                break
            end_idx += 1

        caption_block = "\n".join(lines[caption_line_idx : end_idx + 1])
        # Strip the leading **Figure N.** marker so caption_text is the body.
        caption_text = _MD_CAPTION_START.sub("", caption_block, count=1).strip()
        caption_text = re.sub(r"\s+", " ", caption_text)

        # Provenance comment? Look at the caption block and the lines
        # immediately following (up to 3).
        prov_window_lines = lines[
            caption_line_idx : min(len(lines), end_idx + 4)
        ]
        prov_window = "\n".join(prov_window_lines)
        has_prov = bool(_MARKDOWN_PROVENANCE.search(prov_window))

        blocks.append(
            FigureBlock(
                figure_id=figure_id,
                start_line=i + 1,
                end_line=end_idx + 2,
                caption_text=caption_text,
                includegraphics_path=graphics_path,
                has_provenance_comment=has_prov,
            )
        )
        i = end_idx + 1
    return tuple(blocks)


# --------------------------------------------------------------------------- #
# Bibliography extraction                                                     #
# --------------------------------------------------------------------------- #


def extract_bibliography_keys(
    text: str, fmt: ManuscriptFormat,
) -> tuple[str, ...]:
    """Return all cited bibliography keys in document order, de-duplicated.

    LaTeX: extracts the comma-separated keys inside every
    ``\\cite{...}`` / ``\\citep{...}`` / ``\\citet{...}`` etc.

    Markdown: extracts every pandoc-style ``[@key]`` / ``[-@key]``
    citation, including the multi-key form ``[@a; @b; @c]``.
    """
    if fmt == ManuscriptFormat.latex:
        return _extract_latex_bibkeys(text)
    return _extract_markdown_bibkeys(text)


def _extract_latex_bibkeys(text: str) -> tuple[str, ...]:
    seen: dict[str, None] = {}  # preserve insertion order via dict-keys
    for m in _LATEX_CITE.finditer(text):
        for key in m.group(1).split(","):
            k = key.strip()
            if k and k not in seen:
                seen[k] = None
    return tuple(seen)


def _extract_markdown_bibkeys(text: str) -> tuple[str, ...]:
    seen: dict[str, None] = {}
    for outer in _MD_CITE.finditer(text):
        for inner in _MD_CITE_INNER.finditer(outer.group(0)):
            key = inner.group(1).strip()
            if key and key not in seen:
                seen[key] = None
    return tuple(seen)


# --------------------------------------------------------------------------- #
# Claim extraction                                                            #
# --------------------------------------------------------------------------- #


def _classify_assertion(sentence: str) -> ClaimAssertion:
    """Mirror of :func:`claim_check._classify_assertion`."""
    if _NO_DIFFERENCE_PATTERN.search(sentence):
        return ClaimAssertion.no_difference
    if _NO_CORRELATION_PATTERN.search(sentence):
        return ClaimAssertion.no_correlation
    if _SIGNIFICANT_PATTERN.search(sentence):
        return ClaimAssertion.significant_difference
    if _CORRELATION_PATTERN.search(sentence):
        return ClaimAssertion.correlation_present
    if _EFFECT_SIZE_PATTERN.search(sentence):
        return ClaimAssertion.effect_size_above
    if _DESCRIPTIVE_PATTERN.search(sentence):
        return ClaimAssertion.descriptive
    return ClaimAssertion.unparseable


def _direction(sentence: str) -> str | None:
    if _DIRECTION_HIGHER.search(sentence):
        return "higher"
    if _DIRECTION_LOWER.search(sentence):
        return "lower"
    return None


def _magnitude(sentence: str) -> str | None:
    m = _MAGNITUDE_PATTERN.search(sentence)
    return m.group(1).lower() if m else None


def _split_sentences(text: str) -> list[tuple[int, str]]:
    """Split ``text`` into sentences with their starting character offsets.

    Protects ``Fig.`` so the trailing period is not treated as a
    sentence boundary. Returns ``[(offset, sentence), ...]`` in order.
    """
    sentinel = "\x00"
    protected = re.sub(
        r"\b(Fig|Figs|Eq|Eqs|Eqn|Ref|Refs|et\s+al|i\.e|e\.g|cf|vs)\.",
        lambda m: m.group(0).replace(".", sentinel),
        text,
        flags=re.IGNORECASE,
    )
    out: list[tuple[int, str]] = []
    cur_start = 0
    i = 0
    while i < len(protected):
        ch = protected[i]
        if ch in ".!?":
            # Look ahead for a whitespace boundary.
            j = i + 1
            if j < len(protected) and protected[j] in '"”’\'':
                j += 1
            if j >= len(protected) or protected[j].isspace():
                sent = protected[cur_start : j].replace(sentinel, ".").strip()
                if sent:
                    out.append((cur_start, sent))
                # Skip the trailing whitespace to land on the next char.
                while j < len(protected) and protected[j].isspace():
                    j += 1
                cur_start = j
                i = j
                continue
        i += 1
    # Trailing sentence (no terminal punctuation).
    if cur_start < len(protected):
        tail = protected[cur_start:].replace(sentinel, ".").strip()
        if tail:
            out.append((cur_start, tail))
    return out


def extract_claims(
    text: str,
    figure_refs: tuple[FigureRef, ...] | None = None,
) -> tuple[Claim, ...]:
    """Walk every sentence in ``text``; emit one :class:`Claim` per figure ref.

    A sentence containing two figure references yields two claims with
    the same sentence string and the same assertion.

    Parameters
    ----------
    text
        The raw manuscript text (LaTeX or Markdown).
    figure_refs
        Optional pre-extracted refs. When ``None`` (default), we
        scan sentences for free-text mentions only (``Figure N``,
        ``Fig. N``) — this matches the behaviour of E2's
        :func:`claim_check.extract_claims`. When provided, every ref
        whose ``line_number`` falls inside the sentence is also
        emitted as a claim, so LaTeX ``\\ref{fig:1}`` cross-refs
        produce claims too.

    Returns
    -------
    tuple[Claim, ...]
        Claims in document order.
    """
    claims: list[Claim] = []
    line_offsets = _build_line_offsets(text)
    sentences = _split_sentences(text)

    # Build per-line buckets for fast ref lookup.
    refs_by_line: dict[int, list[FigureRef]] = {}
    if figure_refs:
        for r in figure_refs:
            refs_by_line.setdefault(r.line_number, []).append(r)

    for start_off, sent in sentences:
        sent_line = _line_index_for_offset(line_offsets, start_off) + 1
        end_off = start_off + len(sent)
        end_line = _line_index_for_offset(line_offsets, end_off) + 1
        seen_ids: set[str] = set()

        # 1) Free-text mentions ("Figure 3a", "Fig. 2").
        for m in _FIGURE_MENTION.finditer(sent):
            n = m.group(1)
            sub = m.group(2) or ""
            fig_id = f"fig:{n}{sub.lower()}"
            if fig_id in seen_ids:
                continue
            seen_ids.add(fig_id)
            claims.append(
                Claim(
                    figure_id=fig_id,
                    sentence=sent,
                    assertion=_classify_assertion(sent),
                    direction=_direction(sent),
                    magnitude_qualifier=_magnitude(sent),
                    line_number=sent_line,
                )
            )

        # 2) LaTeX cross-refs whose line falls inside this sentence.
        if figure_refs:
            for line in range(sent_line, end_line + 1):
                for r in refs_by_line.get(line, ()):
                    if r.figure_id in seen_ids:
                        continue
                    seen_ids.add(r.figure_id)
                    claims.append(
                        Claim(
                            figure_id=r.figure_id,
                            sentence=sent,
                            assertion=_classify_assertion(sent),
                            direction=_direction(sent),
                            magnitude_qualifier=_magnitude(sent),
                            line_number=r.line_number,
                        )
                    )
    return tuple(claims)


# --------------------------------------------------------------------------- #
# Section bookkeeping                                                         #
# --------------------------------------------------------------------------- #


_METHODS_NAMES = re.compile(
    r"^(?:STAR\s*Methods|Methods|Materials\s+and\s+Methods|"
    r"Experimental\s+Procedures|Methods\s+and\s+Materials)\b",
    re.IGNORECASE,
)


def _has_methods_section(sections: tuple[Section, ...]) -> bool:
    """Return ``True`` if any heading name matches a Methods convention."""
    return any(_METHODS_NAMES.match(s.name.strip()) for s in sections)


def _has_star_methods(sections: tuple[Section, ...]) -> bool:
    """Return ``True`` if any heading contains the STAR Methods marker."""
    return any(_STAR_METHODS.search(s.name) for s in sections)


def _word_count_by_section(sections: tuple[Section, ...]) -> dict[str, int]:
    """Aggregate word_counts by section name (top-level sections only)."""
    out: dict[str, int] = {}
    for s in sections:
        if s.level != 1:
            continue
        out[s.name] = out.get(s.name, 0) + s.word_count
    return out


# --------------------------------------------------------------------------- #
# LaTeX parser                                                                #
# --------------------------------------------------------------------------- #


def parse_latex(text: str, *, path: Path) -> ExistingManuscript:
    """Parse a LaTeX manuscript string into :class:`ExistingManuscript`.

    Parameters
    ----------
    text
        UTF-8 LaTeX source.
    path
        Path to the source file; embedded verbatim in the record.

    Returns
    -------
    ExistingManuscript
        Structured snapshot.
    """
    title = _extract_latex_title(text)
    venue: str | None = None
    dc_match = _LATEX_DOCUMENTCLASS.search(text)
    if dc_match is not None:
        venue = detect_venue_from_documentclass(dc_match.group(1))

    sections = extract_sections(text, ManuscriptFormat.latex)
    figure_refs = extract_figure_refs(text, ManuscriptFormat.latex)
    figure_blocks = extract_figure_blocks(text, ManuscriptFormat.latex)
    claims = extract_claims(text, figure_refs)
    bib_keys = extract_bibliography_keys(text, ManuscriptFormat.latex)

    n_lines = text.count("\n") + (0 if text.endswith("\n") else 1)
    n_words = _word_count(text)

    return ExistingManuscript(
        path=path,
        format=ManuscriptFormat.latex,
        venue=venue,
        title=title,
        n_lines=n_lines,
        n_words=n_words,
        sections=sections,
        figure_refs=figure_refs,
        figure_blocks=figure_blocks,
        claims=claims,
        bibliography_keys_cited=bib_keys,
        has_methods_section=_has_methods_section(sections),
        has_star_methods=_has_star_methods(sections),
        word_count_by_section=_word_count_by_section(sections),
    )


# --------------------------------------------------------------------------- #
# Markdown parser                                                             #
# --------------------------------------------------------------------------- #


def _parse_markdown_frontmatter(text: str) -> tuple[dict[str, str], int]:
    """Extract a YAML-ish frontmatter block at the top of a markdown file.

    Returns ``({key: value, ...}, offset)`` where ``offset`` is the
    character index of the body (just past the closing ``---``).
    Returns ``({}, 0)`` when no frontmatter is present.
    """
    m = _MD_FRONTMATTER.match(text)
    if m is None:
        return {}, 0
    inner = m.group(1)
    kvs: dict[str, str] = {}
    for ln in inner.splitlines():
        kv = _MD_FRONTMATTER_KV.match(ln)
        if kv is None:
            continue
        key = kv.group(1).strip().lower()
        val = kv.group(2).strip().strip("\"'")
        kvs[key] = val
    return kvs, m.end()


def _markdown_title(text: str, body_offset: int) -> str | None:
    """Extract the title from ``# Heading`` on the first non-blank body line."""
    body = text[body_offset:]
    for ln in body.splitlines():
        if not ln.strip():
            continue
        m = _MD_HEADER.match(ln)
        if m is not None and len(m.group(1)) == 1:
            return m.group(2).strip()
        return None
    return None


def parse_markdown(text: str, *, path: Path) -> ExistingManuscript:
    """Parse a Markdown manuscript string into :class:`ExistingManuscript`.

    Parameters
    ----------
    text
        UTF-8 Markdown source. May include YAML frontmatter.
    path
        Path to the source file; embedded verbatim in the record.

    Returns
    -------
    ExistingManuscript
        Structured snapshot.
    """
    frontmatter, body_off = _parse_markdown_frontmatter(text)
    title = frontmatter.get("title") or _markdown_title(text, body_off)
    venue = frontmatter.get("venue") or None
    # Normalise frontmatter venue against the lookup table.
    if venue is not None:
        v = detect_venue_from_documentclass(venue)
        if v is not None:
            venue = v

    sections = extract_sections(text, ManuscriptFormat.markdown)
    figure_refs = extract_figure_refs(text, ManuscriptFormat.markdown)
    figure_blocks = extract_figure_blocks(text, ManuscriptFormat.markdown)
    claims = extract_claims(text, figure_refs)
    bib_keys = extract_bibliography_keys(text, ManuscriptFormat.markdown)

    n_lines = text.count("\n") + (0 if text.endswith("\n") else 1)
    n_words = _word_count(text)

    return ExistingManuscript(
        path=path,
        format=ManuscriptFormat.markdown,
        venue=venue,
        title=title,
        n_lines=n_lines,
        n_words=n_words,
        sections=sections,
        figure_refs=figure_refs,
        figure_blocks=figure_blocks,
        claims=claims,
        bibliography_keys_cited=bib_keys,
        has_methods_section=_has_methods_section(sections),
        has_star_methods=_has_star_methods(sections),
        word_count_by_section=_word_count_by_section(sections),
    )


# --------------------------------------------------------------------------- #
# Top-level dispatcher                                                        #
# --------------------------------------------------------------------------- #


def parse_manuscript(path: str | Path) -> ExistingManuscript:
    """Detect the format of ``path`` and parse it accordingly.

    Convenience wrapper around :func:`detect_format` +
    :func:`parse_latex` / :func:`parse_markdown`.

    Raises
    ------
    ManuscriptParseError
        If the file cannot be read or its format cannot be detected.
    """
    p = Path(path)
    fmt = detect_format(p)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise ManuscriptParseError(f"cannot read manuscript {p}: {exc}") from exc

    if fmt == ManuscriptFormat.latex:
        return parse_latex(text, path=p)
    return parse_markdown(text, path=p)


# --------------------------------------------------------------------------- #
# Optional pylatexenc enrichment                                              #
# --------------------------------------------------------------------------- #


def enrich_with_pylatexenc(manuscript: ExistingManuscript) -> ExistingManuscript:
    """Optionally re-render captions through ``pylatexenc`` for plain-text output.

    This is a best-effort enrichment hook: when ``pylatexenc`` is
    installed, every :class:`FigureBlock`'s ``caption_text`` is
    replaced with its LaTeX-stripped equivalent (math expressions
    preserved verbatim). When ``pylatexenc`` is not installed, the
    input manuscript is returned unchanged — this function is the
    *only* code path that touches the optional dependency.

    Markdown manuscripts pass through unchanged.
    """
    if manuscript.format != ManuscriptFormat.latex:
        return manuscript
    try:
        from pylatexenc.latex2text import LatexNodes2Text  # type: ignore
    except ImportError:
        return manuscript

    converter = LatexNodes2Text(
        math_mode="verbatim",
        keep_braced_groups=False,
        strict_latex_spaces=False,
    )
    new_blocks = tuple(
        FigureBlock(
            figure_id=b.figure_id,
            start_line=b.start_line,
            end_line=b.end_line,
            caption_text=re.sub(
                r"\s+", " ", converter.latex_to_text(b.caption_text).strip()
            ),
            includegraphics_path=b.includegraphics_path,
            has_provenance_comment=b.has_provenance_comment,
        )
        for b in manuscript.figure_blocks
    )
    return ExistingManuscript(
        path=manuscript.path,
        format=manuscript.format,
        venue=manuscript.venue,
        title=manuscript.title,
        n_lines=manuscript.n_lines,
        n_words=manuscript.n_words,
        sections=manuscript.sections,
        figure_refs=manuscript.figure_refs,
        figure_blocks=new_blocks,
        claims=manuscript.claims,
        bibliography_keys_cited=manuscript.bibliography_keys_cited,
        has_methods_section=manuscript.has_methods_section,
        has_star_methods=manuscript.has_star_methods,
        word_count_by_section=manuscript.word_count_by_section,
    )
