"""Quality rules for meta_and_diagnostic families."""

from __future__ import annotations


def _lines(fig):
    out = []
    for a in fig.axes:
        out.extend(a.get_lines())
    return out


def assert_diagnostic_curve_ok(fig, entry):
    """Diagnostic curve — ≥2 lines AND ≥1 legend entry."""
    lines = _lines(fig)
    assert len(lines) >= 2, f"{entry.full_name}: needs ≥2 curves (got {len(lines)})"
    has_legend = any(a.get_legend() is not None for a in fig.axes)
    assert has_legend, f"{entry.full_name}: needs a legend"


def assert_ladder_ok(fig, entry):
    """Ladder family — ≥3 horizontal bars, at least one labelled numeric."""
    n_bars = sum(len(a.patches) for a in fig.axes)
    assert n_bars >= 3, f"{entry.full_name}: needs ≥3 ladder rungs (got {n_bars})"


def assert_radar_ok(fig, entry):
    """Radar family — at least one polar axis and ≥1 filled polygon."""
    polar = [a for a in fig.axes if getattr(a, "name", "") == "polar"]
    assert len(polar) >= 1, f"{entry.full_name}: needs a polar axis"
    # ax.fill(...) returns Polygon patches stored on ax.patches; ax.scatter
    # returns a PathCollection on ax.collections. Require at least one of
    # either fill polygon or line — the radar must have something to read.
    n_filled = 0
    n_lines = 0
    for a in polar:
        n_filled += sum(1 for p in a.patches if type(p).__name__ == "Polygon")
        n_lines += len(a.get_lines())
    assert n_filled + n_lines >= 2, (
        f"{entry.full_name}: needs ≥2 drawn objects (filled polygons + lines); "
        f"got {n_filled} filled, {n_lines} lines"
    )
