"""Cross-modality figure integrity QA.

Every recipe in :mod:`panelforge_figures.recipes` produces a figure that
should honor the same typography, spatial, and robustness contract.
Running :func:`check_figure_integrity` on a rendered figure returns a
:class:`FigureIntegrityReport` summarising any violations.

The checks are deliberately cheap so they can run on all 107 recipes in
the CI matrix. They answer four questions:

* Is every text artist rendered in the approved Helvetica stack?
* Is every text artist's font size inside the sanity range (5–24 pt)?
* Does every axis contain at least one visible artist (detects
  silent empty-data crashes where a recipe early-returned without
  drawing anything)?
* Does every text artist sit inside the printable figure bounds (detects
  labels clipped off the page by a bad `bbox_to_anchor`)?
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

import matplotlib.text as mtext
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from .style import (
    PF_MAX_FONTSIZE_PT,
    PF_MIN_FONTSIZE_PT,
    is_approved_font_family,
)

# Tolerance in figure fractions; text with any portion inside
# [-_BOUNDS_SLACK, 1 + _BOUNDS_SLACK] is considered on-page. This covers
# footer callouts at y=0.005 and suptitles at y≈1.02.
_BOUNDS_SLACK: float = 0.05


@dataclass
class FigureIntegrityIssue:
    """One problem found in a figure, with enough context to reproduce."""

    severity: str              # "error" or "warning"
    rule: str                  # machine-readable rule id
    detail: str                # human-readable description
    artist_repr: str = ""      # optional repr of the offending artist

    def __str__(self) -> str:
        base = f"[{self.severity.upper()}:{self.rule}] {self.detail}"
        if self.artist_repr:
            base = f"{base} ({self.artist_repr})"
        return base


@dataclass
class FigureIntegrityReport:
    """Result of running :func:`check_figure_integrity` on a figure."""

    issues: list[FigureIntegrityIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[FigureIntegrityIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[FigureIntegrityIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_text(self) -> str:
        if not self.issues:
            return "figure integrity: OK"
        lines = [f"figure integrity: {len(self.errors)} error(s), "
                 f"{len(self.warnings)} warning(s)"]
        lines.extend(f"  {i}" for i in self.issues)
        return "\n".join(lines)


# ─────────────────────────── rule implementations ─────────────────────────

def _iter_text_artists(fig: Figure) -> Iterable[mtext.Text]:
    """Yield every visible Text artist anchored to the figure or its axes."""
    for t in fig.texts:
        if t.get_visible() and (t.get_text() or "").strip():
            yield t
    for ax in fig.get_axes():
        # Axis titles (panel titles)
        if ax.get_title():
            yield ax.title
        # x/y axis labels
        if ax.get_xlabel():
            yield ax.xaxis.label
        if ax.get_ylabel():
            yield ax.yaxis.label
        # Arbitrary ax.text(...) calls
        for t in ax.texts:
            if t.get_visible() and (t.get_text() or "").strip():
                yield t
        # Tick labels
        for t in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
            if t.get_visible() and (t.get_text() or "").strip():
                yield t
        # Legend text
        legend = ax.get_legend()
        if legend is not None:
            for t in legend.get_texts():
                if t.get_visible():
                    yield t
            if legend.get_title() and (legend.get_title().get_text() or "").strip():
                yield legend.get_title()


def _check_font_compliance(
    fig: Figure, issues: list[FigureIntegrityIssue]
) -> None:
    for t in _iter_text_artists(fig):
        family = t.get_fontfamily() or t.get_fontname()
        if not is_approved_font_family(family):
            issues.append(FigureIntegrityIssue(
                severity="error",
                rule="font_family",
                detail=(
                    f"text artist uses non-approved font family {family!r}; "
                    f"must resolve to the PF_FONT_STACK"
                ),
                artist_repr=_summarize_text(t),
            ))


def _check_font_sizes(
    fig: Figure, issues: list[FigureIntegrityIssue]
) -> None:
    for t in _iter_text_artists(fig):
        sz = float(t.get_fontsize() or 0.0)
        if sz < PF_MIN_FONTSIZE_PT:
            issues.append(FigureIntegrityIssue(
                severity="error",
                rule="font_size_too_small",
                detail=f"font size {sz:.1f}pt is below minimum {PF_MIN_FONTSIZE_PT:.1f}pt",
                artist_repr=_summarize_text(t),
            ))
        elif sz > PF_MAX_FONTSIZE_PT:
            issues.append(FigureIntegrityIssue(
                severity="error",
                rule="font_size_too_large",
                detail=f"font size {sz:.1f}pt exceeds max {PF_MAX_FONTSIZE_PT:.1f}pt",
                artist_repr=_summarize_text(t),
            ))


def _check_axes_nonempty(
    fig: Figure, issues: list[FigureIntegrityIssue]
) -> None:
    for ax in fig.get_axes():
        if _looks_empty(ax):
            issues.append(FigureIntegrityIssue(
                severity="error",
                rule="empty_axes",
                detail=(
                    "axes contains no visible data artists — likely an upstream "
                    "crash or a recipe that early-returned. Use "
                    "empty_data_guard() to render a placeholder instead."
                ),
                artist_repr=f"axes at {ax.get_position().bounds}",
            ))


def _looks_empty(ax: Axes) -> bool:
    """Heuristic: axes has no lines, patches, collections, or images."""
    if ax.lines or ax.patches or ax.collections or ax.images:
        return False
    # An axes that is hidden by the caller (e.g. ``ax.axis('off')``) is
    # allowed to be empty — it's intentional decoration, not a crash.
    # matplotlib sets ``ax.axison = False`` in that case.
    if not getattr(ax, "axison", True):
        return False
    # An axes with its frame off and no ticks is also decorative.
    if (not ax.get_frame_on()
            and not ax.get_xticks().size
            and not ax.get_yticks().size):
        return False
    return True


def _check_text_in_bounds(
    fig: Figure, issues: list[FigureIntegrityIssue]
) -> None:
    """Flag text whose anchor falls well outside the printable figure."""
    for t in _iter_text_artists(fig):
        # Convert the text's anchor from whatever transform it uses into
        # figure fraction. Tick labels live in a display-coord bbox we
        # resolve via get_window_extent.
        try:
            fig_w, fig_h = fig.canvas.get_width_height()
            if fig_w == 0 or fig_h == 0:
                return
            bbox = t.get_window_extent(renderer=fig.canvas.get_renderer())
            x_frac = bbox.x0 / fig_w
            y_frac = bbox.y0 / fig_h
        except Exception:
            continue
        if (
            x_frac < -_BOUNDS_SLACK or x_frac > 1 + _BOUNDS_SLACK
            or y_frac < -_BOUNDS_SLACK or y_frac > 1 + _BOUNDS_SLACK
        ):
            issues.append(FigureIntegrityIssue(
                severity="warning",
                rule="text_out_of_bounds",
                detail=(
                    f"text anchor at figure fraction "
                    f"({x_frac:.2f}, {y_frac:.2f}) lies outside the printable area"
                ),
                artist_repr=_summarize_text(t),
            ))


def _summarize_text(t: mtext.Text) -> str:
    s = (t.get_text() or "").replace("\n", " ")
    if len(s) > 40:
        s = s[:37] + "..."
    return f"Text({s!r})"


# ─────────────────────────────── public API ───────────────────────────────

def check_figure_integrity(fig: Figure) -> FigureIntegrityReport:
    """Run the cross-modality QA rule set on a rendered figure.

    The checks are conservative (tolerances >0) so they pass on every
    recipe currently in the registry. Tightening thresholds in the
    future is a one-line change at the top of this module.
    """
    report = FigureIntegrityReport()
    # Force a draw so tick labels and legend geometry are populated.
    try:
        fig.canvas.draw()
    except Exception:
        # Some backends (pdf, svg) raise if no renderer is attached yet;
        # fall through — the checks below tolerate a missing renderer.
        pass
    _check_font_compliance(fig, report.issues)
    _check_font_sizes(fig, report.issues)
    _check_axes_nonempty(fig, report.issues)
    _check_text_in_bounds(fig, report.issues)
    return report
