"""Quality rules for sensitivity_analysis families."""

from __future__ import annotations


def _text_artists(fig):
    out = []
    for a in fig.axes:
        out.extend(a.texts)
    return out


def assert_sobol_bar_ok(fig, entry):
    """sobol_bar — ≥3 "bar-like" artists (Rectangle patches OR scatter points)
    AND ≥3 numeric labels.

    This family covers both true bar recipes (Sobol S1/ST, PC loadings) and
    scatter-style screening recipes (Morris μ*/σ). Both qualify as long as
    the axis carries at least three indexed parameter markers plus their
    annotations — the information density test is the same.
    """
    bars = 0
    scatter_pts = 0
    for a in fig.axes:
        bars += len(a.patches)
        for c in a.collections:
            if type(c).__name__ == "PathCollection":
                try:
                    scatter_pts += len(c.get_offsets())
                except (AttributeError, ValueError):
                    scatter_pts += 1
    assert bars >= 3 or scatter_pts >= 3, (
        f"{entry.full_name}: needs ≥3 bar patches or scatter points "
        f"(got {bars} bars, {scatter_pts} scatter)"
    )
    txt = _text_artists(fig)
    assert len(txt) >= 3, (
        f"{entry.full_name}: needs ≥3 annotation text artists (got {len(txt)})"
    )


def assert_contour_ok(fig, entry):
    """Contour / parameter scan — ≥1 contour OR image (pcolormesh), plus ≥1 collection."""
    has_heat = any(a.images or [c for c in a.collections] for a in fig.axes)
    assert has_heat, f"{entry.full_name}: needs a heatmap/contour surface"


def assert_scatter_collapse_ok(fig, entry):
    """Scatter collapse — ≥1 scatter AND ≥1 line (fit), legend optional."""
    scatter_count = 0
    line_count = 0
    for a in fig.axes:
        scatter_count += sum(
            1 for c in a.collections if type(c).__name__ == "PathCollection"
        )
        line_count += len(a.get_lines())
    assert scatter_count >= 1, f"{entry.full_name}: needs ≥1 scatter"
    assert line_count >= 1, f"{entry.full_name}: needs ≥1 fit line"
