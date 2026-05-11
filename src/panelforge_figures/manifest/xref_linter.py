"""Cross-reference linter — Elevation 13 (v3.7.0).

Lints a manuscript for figure-reference issues before submission.
Built on E10's :mod:`manuscript_parse` infrastructure: parses the
manuscript once, then cross-references the resulting
:class:`ExistingManuscript` against the rendered figures on disk.

The linter is best-effort and tolerant — every check produces a
:class:`LintFinding` rather than raising. Callers consume the
:class:`LintReport` (sorted by severity then ``figure_id``) and decide
whether to block submission. The CLI surface (``figures lint xrefs``)
exits non-zero on any error finding so it can be wired into pre-submission
hooks.

The eight finding kinds catch the most common manuscript-figure mistakes:

* ``ref_without_block``      — ``\\ref{fig:N}`` in text but no figure
  block defines ``\\label{fig:N}``.  **Error** (publication-blocking).
* ``block_without_ref``      — figure block defined but its label is
  never referenced in prose.  **Warning**.
* ``duplicate_block``        — same ``\\label{fig:N}`` appears in two
  different ``\\begin{figure}`` blocks.  **Error**.
* ``caption_missing``        — figure block has no ``\\caption``
  command at all.  **Error**.
* ``caption_too_short``      — caption is below ``min_caption_chars``
  (default 30).  **Warning**.
* ``rendered_file_missing``  — ``\\includegraphics{...}`` path does
  not resolve to a real file relative to the manuscript directory.
  **Error**.
* ``orphan_figure``          — a file exists in ``figures_dir`` whose
  filename stem cannot be matched to any ``\\ref`` or ``\\label`` in
  the manuscript.  **Warning**.
* ``orphan_ref``             — same as ``ref_without_block`` but
  emitted when no figure block exists at all (vs. block exists but for
  a different ``fig:N``).  Reserved for future use; currently
  ``ref_without_block`` covers both cases.

Design notes
------------

* The linter **does not** mutate the manuscript or filesystem.
* The linter **lazy-imports** ``manuscript_parse`` so importing
  :mod:`xref_linter` is cheap even when the parser is not needed.
* All public types are frozen dataclasses and tuples — the report is
  safe to share across threads and JSON-serialisable via
  :meth:`LintReport.to_dict`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

__all__ = [
    "FindingKind",
    "FindingSeverity",
    "LintError",
    "LintFinding",
    "LintReport",
    "lint_xrefs",
    "render_lint_report_markdown",
]


# --------------------------------------------------------------------------- #
# Enums + errors                                                              #
# --------------------------------------------------------------------------- #


class FindingSeverity(StrEnum):
    """Severity of a lint finding.

    ``error``    — publication-blocking issue (CLI exits 1).
    ``warning``  — should review (CLI exits 1 only with --fail-on-warning).
    ``info``     — informational only.
    """

    error = "error"
    warning = "warning"
    info = "info"


class FindingKind(StrEnum):
    """Discriminator for the underlying problem the linter detected."""

    orphan_ref = "orphan_ref"                       # \ref{fig:N} in text, no figure rendered
    orphan_figure = "orphan_figure"                  # figure rendered, no \ref in text
    ref_without_block = "ref_without_block"          # \ref{fig:N} but no \begin{figure} block
    block_without_ref = "block_without_ref"          # \begin{figure} but never referenced
    duplicate_block = "duplicate_block"              # same fig:N defined twice
    duplicate_ref = "duplicate_ref"                  # fig:N referenced many times (info)
    rendered_file_missing = "rendered_file_missing"  # \includegraphics path doesn't exist
    caption_too_short = "caption_too_short"          # caption < min_caption_chars
    caption_missing = "caption_missing"              # \begin{figure} with no \caption


class LintError(RuntimeError):
    """Raised when the linter cannot proceed (e.g. manuscript unreadable)."""


# --------------------------------------------------------------------------- #
# Dataclasses                                                                 #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class LintFinding:
    """A single lint observation tied to a figure id.

    The dataclass is immutable so callers can safely collect findings
    into sets / dicts keyed by ``(kind, figure_id)`` for deduplication.

    Attributes
    ----------
    kind
        Discriminator for the underlying problem.
    severity
        Triage severity (``error`` / ``warning`` / ``info``).
    figure_id
        Canonical figure id (typically ``fig:N`` or a filename stem).
    message
        Human-readable summary suitable for terminal / markdown output.
    line_number
        1-indexed line in the manuscript when the finding ties to a
        specific text location; ``None`` when the finding is about a
        rendered file with no manuscript locus.
    file_path
        Absolute path to a rendered file when the finding involves the
        filesystem (``rendered_file_missing``, ``orphan_figure``);
        ``None`` otherwise.
    """

    kind: FindingKind
    severity: FindingSeverity
    figure_id: str
    message: str
    line_number: int | None = None
    file_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        """Render as a JSON-serialisable dict."""
        return {
            "kind": self.kind.value,
            "severity": self.severity.value,
            "figure_id": self.figure_id,
            "message": self.message,
            "line_number": self.line_number,
            "file_path": str(self.file_path) if self.file_path is not None else None,
        }


@dataclass(frozen=True)
class LintReport:
    """Aggregated linter output for a single manuscript.

    The report is JSON-serialisable and ordered: findings are sorted by
    ``(severity, figure_id)`` so the terminal output reads top-down from
    most critical to least critical.
    """

    manuscript_path: Path
    figures_dir: Path | None
    findings: tuple[LintFinding, ...]
    n_errors: int
    n_warnings: int
    n_info: int
    n_referenced: int       # total \ref occurrences
    n_blocks: int           # total \begin{figure} blocks
    n_rendered: int         # total files in figures_dir
    verdict: str            # "clean" / "warnings" / "errors"

    def to_dict(self) -> dict[str, Any]:
        """Render as a JSON-serialisable dict."""
        return {
            "manuscript_path": str(self.manuscript_path),
            "figures_dir": (
                str(self.figures_dir) if self.figures_dir is not None else None
            ),
            "findings": [f.to_dict() for f in self.findings],
            "n_errors": self.n_errors,
            "n_warnings": self.n_warnings,
            "n_info": self.n_info,
            "n_referenced": self.n_referenced,
            "n_blocks": self.n_blocks,
            "n_rendered": self.n_rendered,
            "verdict": self.verdict,
        }


# --------------------------------------------------------------------------- #
# Filename -> figure_id inference                                             #
# --------------------------------------------------------------------------- #


# Matches:  figure_1 / fig_1 / panel_1 / figure1 / fig1 / figure 1
#           figure_1a / fig-3b / panel_2_a / figure_03
_STEM_PATTERN = re.compile(
    r"^(?P<prefix>figure|fig|panel)[_\s\-]?0*(?P<n>\d+)[_\s\-]?(?P<sub>[a-z]?)$",
    re.IGNORECASE,
)


def _infer_figure_ids_from_filename(stem: str) -> tuple[str, ...]:
    """Map a filename stem to plausible figure ids in the manuscript.

    The linter cannot know a priori how the author named their LaTeX
    labels (``\\label{fig:1}`` vs ``\\label{figure_1}`` vs
    ``\\label{fig:overview}``), so we generate a small candidate set
    from the filename and test each against the manuscript's actual
    refs/blocks.

    Examples
    --------
    >>> _infer_figure_ids_from_filename("figure_1")
    ('fig:1', 'figure_1', 'figure:1', '1')
    >>> _infer_figure_ids_from_filename("figure_3b")
    ('fig:3b', 'figure_3b', 'figure:3b', '3b')
    >>> _infer_figure_ids_from_filename("fig_2")
    ('fig:2', 'figure_2', 'figure:2', '2')
    >>> _infer_figure_ids_from_filename("panel-1-a")
    ('fig:1a', 'figure_1a', 'figure:1a', '1a')
    >>> _infer_figure_ids_from_filename("overview")
    ('overview',)
    """
    lowered = stem.lower().strip()
    m = _STEM_PATTERN.match(lowered)
    if m is None:
        return (lowered,)
    n = m.group("n").lstrip("0") or "0"
    sub = (m.group("sub") or "").lower()
    suffix = f"{n}{sub}"
    return (f"fig:{suffix}", f"figure_{suffix}", f"figure:{suffix}", suffix)


# --------------------------------------------------------------------------- #
# Main entry point                                                            #
# --------------------------------------------------------------------------- #


def lint_xrefs(
    manuscript_path: Path,
    *,
    figures_dir: Path | None = None,
    min_caption_chars: int = 30,
    figure_extensions: tuple[str, ...] = (".pdf", ".png", ".svg"),
) -> LintReport:
    """Cross-reference linter for a manuscript.

    Uses :func:`panelforge_figures.manifest.manuscript_parse.parse_manuscript`
    (E10) to parse the manuscript, then cross-references:

      1. ``figure_refs`` vs ``figure_blocks`` (within manuscript) →
         ``ref_without_block`` and ``block_without_ref``.
      2. ``figure_blocks`` against themselves → ``duplicate_block``.
      3. caption quality checks → ``caption_missing`` /
         ``caption_too_short``.
      4. ``\\includegraphics`` paths vs filesystem →
         ``rendered_file_missing``.
      5. rendered files vs ``figure_refs`` / ``figure_blocks`` →
         ``orphan_figure``.

    Parameters
    ----------
    manuscript_path
        Path to the manuscript ``.tex`` or ``.md`` file.
    figures_dir
        Optional directory containing rendered figure files (pdf/png/svg).
        When ``None`` or non-existent, orphan-figure detection is skipped.
    min_caption_chars
        Minimum acceptable caption length (after whitespace strip).
        Captions shorter than this emit a ``caption_too_short`` warning.
    figure_extensions
        File extensions considered "rendered figures" when scanning
        ``figures_dir``.  Case-insensitive matching is applied.

    Returns
    -------
    LintReport
        All findings sorted by ``(severity, figure_id)`` plus aggregate
        counters and a top-level ``verdict`` string.

    Raises
    ------
    LintError
        When the manuscript parser itself fails (unreadable file or
        unrecognised format).
    """
    # Lazy-import the parser so importing this module is cheap.
    try:
        from panelforge_figures.manifest.manuscript_parse import (
            ManuscriptParseError,
            parse_manuscript,
        )
    except ImportError as exc:  # pragma: no cover — defensive
        raise LintError(
            f"cannot import manuscript_parse (E10 dependency): {exc}"
        ) from exc

    try:
        existing = parse_manuscript(manuscript_path)
    except ManuscriptParseError as exc:
        raise LintError(f"cannot parse manuscript {manuscript_path}: {exc}") from exc

    findings: list[LintFinding] = []
    ref_ids = {r.figure_id for r in existing.figure_refs}
    block_ids = {b.figure_id for b in existing.figure_blocks}

    # ---- Check 1: \ref{fig:N} with no figure block defined --------------
    seen_ref_ids: set[str] = set()
    for ref in existing.figure_refs:
        if ref.figure_id in seen_ref_ids:
            continue
        seen_ref_ids.add(ref.figure_id)
        if ref.figure_id not in block_ids:
            findings.append(
                LintFinding(
                    kind=FindingKind.ref_without_block,
                    severity=FindingSeverity.error,
                    figure_id=ref.figure_id,
                    message=(
                        f"\\ref{{{ref.figure_id}}} on line {ref.line_number} "
                        f"but no figure block defines this label"
                    ),
                    line_number=ref.line_number,
                )
            )

    # ---- Check 2: figure block with no \ref pointing to it --------------
    for block in existing.figure_blocks:
        # An empty figure_id means the block lacks a \label entirely;
        # caption_missing / similar checks cover that case below, but
        # treat the missing label itself as a block-without-ref so the
        # author notices.
        if not block.figure_id:
            findings.append(
                LintFinding(
                    kind=FindingKind.block_without_ref,
                    severity=FindingSeverity.warning,
                    figure_id="<no-label>",
                    message=(
                        f"Figure block at line {block.start_line} has no "
                        f"\\label — cannot be cross-referenced"
                    ),
                    line_number=block.start_line,
                )
            )
            continue
        if block.figure_id not in ref_ids:
            findings.append(
                LintFinding(
                    kind=FindingKind.block_without_ref,
                    severity=FindingSeverity.warning,
                    figure_id=block.figure_id,
                    message=(
                        f"Figure block {block.figure_id} defined on line "
                        f"{block.start_line} but never referenced in text"
                    ),
                    line_number=block.start_line,
                )
            )

    # ---- Check 3: duplicate figure block labels --------------------------
    block_id_counts: dict[str, int] = {}
    block_id_first_line: dict[str, int] = {}
    for block in existing.figure_blocks:
        if not block.figure_id:
            continue
        block_id_counts[block.figure_id] = (
            block_id_counts.get(block.figure_id, 0) + 1
        )
        block_id_first_line.setdefault(block.figure_id, block.start_line)
    for fig_id, count in block_id_counts.items():
        if count > 1:
            findings.append(
                LintFinding(
                    kind=FindingKind.duplicate_block,
                    severity=FindingSeverity.error,
                    figure_id=fig_id,
                    message=(
                        f"Figure block {fig_id} defined {count} times "
                        f"(only the first at line {block_id_first_line[fig_id]} "
                        f"will be linked by LaTeX)"
                    ),
                    line_number=block_id_first_line[fig_id],
                )
            )

    # ---- Check 4: caption presence + length ------------------------------
    for block in existing.figure_blocks:
        if not block.figure_id:
            # No label means downstream checks cannot key by figure_id
            # — caption issues for such blocks were already surfaced via
            # block_without_ref above.
            continue
        stripped = (block.caption_text or "").strip()
        if not stripped:
            findings.append(
                LintFinding(
                    kind=FindingKind.caption_missing,
                    severity=FindingSeverity.error,
                    figure_id=block.figure_id,
                    message=(
                        f"Figure {block.figure_id} has no caption "
                        f"(\\caption{{...}} missing or empty)"
                    ),
                    line_number=block.start_line,
                )
            )
        elif len(stripped) < min_caption_chars:
            findings.append(
                LintFinding(
                    kind=FindingKind.caption_too_short,
                    severity=FindingSeverity.warning,
                    figure_id=block.figure_id,
                    message=(
                        f"Figure {block.figure_id} caption is only "
                        f"{len(stripped)} chars (recommend >={min_caption_chars})"
                    ),
                    line_number=block.start_line,
                )
            )

    # ---- Check 5: \includegraphics path resolves on disk -----------------
    for block in existing.figure_blocks:
        if block.includegraphics_path is None:
            continue
        candidate = manuscript_path.parent / block.includegraphics_path
        if not _resolves_to_file(candidate):
            findings.append(
                LintFinding(
                    kind=FindingKind.rendered_file_missing,
                    severity=FindingSeverity.error,
                    figure_id=block.figure_id or block.includegraphics_path,
                    message=(
                        f"\\includegraphics path {block.includegraphics_path!r} "
                        f"does not resolve to a real file "
                        f"(searched: {candidate})"
                    ),
                    line_number=block.start_line,
                    file_path=candidate,
                )
            )

    # ---- Check 6: orphan rendered files (figures_dir scan) ---------------
    n_rendered = 0
    if figures_dir is not None and figures_dir.exists():
        rendered_files: list[Path] = []
        lower_exts = {e.lower() for e in figure_extensions}
        for f in figures_dir.rglob("*"):
            if not f.is_file():
                continue
            if f.suffix.lower() in lower_exts:
                rendered_files.append(f)
        n_rendered = len(rendered_files)
        for f in rendered_files:
            stem = f.stem
            inferred_ids = _infer_figure_ids_from_filename(stem)
            # An orphan is a rendered file we cannot match to any ref
            # OR block.  We check both: a figure that's only embedded
            # (block but no ref) is still surfaced by check 2, but the
            # filesystem file itself is "linked" so we don't double-flag.
            if any(i in ref_ids or i in block_ids for i in inferred_ids):
                continue
            # Also exempt files actually used by an \includegraphics path
            # (the includegraphics check covers them already if missing).
            if _used_by_includegraphics(
                f, existing.figure_blocks, manuscript_path.parent
            ):
                continue
            try:
                display_rel = f.relative_to(figures_dir.parent)
            except ValueError:
                display_rel = f
            findings.append(
                LintFinding(
                    kind=FindingKind.orphan_figure,
                    severity=FindingSeverity.warning,
                    figure_id=stem,
                    message=(
                        f"Rendered file {display_rel} appears to have no "
                        f"\\ref or \\label in manuscript "
                        f"(tried ids: {', '.join(inferred_ids)})"
                    ),
                    file_path=f,
                )
            )

    # ---- Counters + verdict ----------------------------------------------
    n_errors = sum(1 for f in findings if f.severity == FindingSeverity.error)
    n_warnings = sum(1 for f in findings if f.severity == FindingSeverity.warning)
    n_info = sum(1 for f in findings if f.severity == FindingSeverity.info)
    if n_errors > 0:
        verdict = "errors"
    elif n_warnings > 0:
        verdict = "warnings"
    else:
        verdict = "clean"

    return LintReport(
        manuscript_path=manuscript_path,
        figures_dir=figures_dir,
        findings=tuple(
            sorted(
                findings,
                key=lambda f: (_severity_rank(f.severity), f.figure_id, f.kind.value),
            )
        ),
        n_errors=n_errors,
        n_warnings=n_warnings,
        n_info=n_info,
        n_referenced=len(existing.figure_refs),
        n_blocks=len(existing.figure_blocks),
        n_rendered=n_rendered,
        verdict=verdict,
    )


def _severity_rank(s: FindingSeverity) -> int:
    """Numeric rank so errors sort before warnings before info."""
    return {
        FindingSeverity.error: 0,
        FindingSeverity.warning: 1,
        FindingSeverity.info: 2,
    }[s]


def _resolves_to_file(candidate: Path) -> bool:
    """Return ``True`` when ``candidate`` (or an extension-completed form) exists.

    LaTeX's ``\\includegraphics{foo}`` is happy with a stem — the engine
    appends ``.pdf`` / ``.png`` / etc.  So we treat the path as
    "resolved" if any extension-completed variant exists, in addition
    to the literal path.
    """
    if candidate.exists() and candidate.is_file():
        return True
    if candidate.suffix == "":
        for ext in (".pdf", ".png", ".jpg", ".jpeg", ".svg", ".eps"):
            if (candidate.parent / f"{candidate.name}{ext}").is_file():
                return True
    return False


def _used_by_includegraphics(
    rendered: Path,
    blocks: tuple[Any, ...],
    manuscript_dir: Path,
) -> bool:
    """Return ``True`` when ``rendered`` is the target of any \\includegraphics.

    We resolve every block's ``includegraphics_path`` against the
    manuscript directory (and, when the path is extensionless, against
    the rendered file's actual extension) and compare via ``samefile``
    when possible, falling back to a resolved-path string match.
    """
    try:
        rendered_resolved = rendered.resolve()
    except OSError:
        rendered_resolved = rendered
    for block in blocks:
        path = getattr(block, "includegraphics_path", None)
        if path is None:
            continue
        target = manuscript_dir / path
        candidates: list[Path] = [target]
        if target.suffix == "":
            candidates.append(target.with_suffix(rendered.suffix))
        for c in candidates:
            try:
                c_resolved = c.resolve()
            except OSError:
                c_resolved = c
            if c_resolved == rendered_resolved:
                return True
            try:
                if c.exists() and c.samefile(rendered):
                    return True
            except OSError:
                pass
    return False


# --------------------------------------------------------------------------- #
# Markdown renderer                                                           #
# --------------------------------------------------------------------------- #


def render_lint_report_markdown(report: LintReport) -> str:
    """Render a :class:`LintReport` as a human-readable markdown document.

    The output is grouped by severity (errors → warnings → info) and
    contains a small header summary so a reader can triage at a glance.
    """
    lines: list[str] = []
    lines.append("# Cross-reference Lint Report")
    lines.append("")
    lines.append(f"**Manuscript**: `{report.manuscript_path}`")
    if report.figures_dir is not None:
        lines.append(f"**Figures dir**: `{report.figures_dir}`")
    verdict_emoji = {
        "clean": "ok",
        "warnings": "review",
        "errors": "FAIL",
    }.get(report.verdict, report.verdict)
    lines.append(
        f"**Verdict**: {report.verdict} ({verdict_emoji})  ·  "
        f"{report.n_errors} errors / {report.n_warnings} warnings / "
        f"{report.n_info} info"
    )
    lines.append(
        f"**Stats**: {report.n_referenced} refs · "
        f"{report.n_blocks} blocks · "
        f"{report.n_rendered} rendered files"
    )
    lines.append("")

    if not report.findings:
        lines.append("No findings. Manuscript cross-references are clean.")
        lines.append("")
        return "\n".join(lines)

    # Group by severity in deterministic order.
    by_sev: dict[FindingSeverity, list[LintFinding]] = {
        FindingSeverity.error: [],
        FindingSeverity.warning: [],
        FindingSeverity.info: [],
    }
    for f in report.findings:
        by_sev[f.severity].append(f)

    section_titles = {
        FindingSeverity.error: "Errors",
        FindingSeverity.warning: "Warnings",
        FindingSeverity.info: "Info",
    }
    for sev in (
        FindingSeverity.error,
        FindingSeverity.warning,
        FindingSeverity.info,
    ):
        findings = by_sev[sev]
        if not findings:
            continue
        lines.append(f"## {section_titles[sev]} ({len(findings)})")
        lines.append("")
        for f in findings:
            header = f"### `{f.figure_id}` — {f.kind.value}"
            lines.append(header)
            if f.line_number is not None:
                lines.append(f"Line {f.line_number}: {f.message}")
            else:
                lines.append(f.message)
            if f.file_path is not None:
                lines.append(f"File: `{f.file_path}`")
            lines.append("")

    return "\n".join(lines)
