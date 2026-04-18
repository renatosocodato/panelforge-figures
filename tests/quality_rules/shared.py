"""Quality rules for families shared across modalities:
heatmap, ridge_by_group, timecourse_hierarchical_ci.
"""

from __future__ import annotations

# Matplotlib ≥ 3.9 returns `FillBetweenPolyCollection` from `fill_between`
# and plain `PolyCollection` from `ax.fill`. Both count as filled polygons
# for our rules.
_FILL_TYPES = {"PolyCollection", "FillBetweenPolyCollection"}


def _count_fills(a):
    return sum(1 for c in a.collections if type(c).__name__ in _FILL_TYPES)


def assert_heatmap_ok(fig, entry):
    """heatmap — needs imshow/pcolormesh (image or QuadMesh collection)."""
    has_heat = False
    for a in fig.axes:
        if a.images:
            has_heat = True
            break
        for c in a.collections:
            if type(c).__name__ in ("QuadMesh", "PolyQuadMesh"):
                has_heat = True
                break
        if has_heat:
            break
    assert has_heat, (
        f"{entry.full_name}: heatmap needs an imshow or pcolormesh surface."
    )


def assert_ridge_by_group_ok(fig, entry):
    """ridge_by_group — stacked filled polygons, ≥2."""
    n_fills = sum(_count_fills(a) for a in fig.axes)
    assert n_fills >= 2, (
        f"{entry.full_name}: ridge needs ≥2 stacked filled densities "
        f"(got {n_fills})."
    )


def assert_timecourse_hierarchical_ci_ok(fig, entry):
    """timecourse_hierarchical_ci — ≥1 filled CI band AND ≥1 mean line."""
    n_fills = sum(_count_fills(a) for a in fig.axes)
    n_lines = sum(len(a.get_lines()) for a in fig.axes)
    assert n_fills >= 1, (
        f"{entry.full_name}: timecourse needs ≥1 filled CI band (got {n_fills})."
    )
    assert n_lines >= 1, (
        f"{entry.full_name}: timecourse needs ≥1 mean line (got {n_lines})."
    )


def assert_split_violin_ok(fig, entry):
    """split_violin — ≥2 violin bodies + ≥1 median marker (scatter).

    matplotlib ≥3.11 returns `FillBetweenPolyCollection` from `ax.violinplot`
    (older versions returned plain `PolyCollection`). Both count as a body.
    """
    n_violin_fills = 0
    n_scatter = 0
    for a in fig.axes:
        for c in a.collections:
            name = type(c).__name__
            if name in _FILL_TYPES:
                n_violin_fills += 1
            elif name == "PathCollection":
                n_scatter += 1
    assert n_violin_fills >= 2, (
        f"{entry.full_name}: split_violin needs ≥2 violin bodies "
        f"(got {n_violin_fills})."
    )
    assert n_scatter >= 1, (
        f"{entry.full_name}: split_violin needs ≥1 median marker "
        f"(got {n_scatter})."
    )


def assert_hysteresis_loop_ok(fig, entry):
    """hysteresis_loop — ≥2 paths (forward + reverse) and a closed-loop gap."""
    n_lines = sum(len(a.get_lines()) for a in fig.axes)
    assert n_lines >= 2, (
        f"{entry.full_name}: hysteresis needs ≥2 curves (forward + reverse); "
        f"got {n_lines}."
    )


def assert_coef_forest_ok(fig, entry):
    """coef_forest — ≥3 estimate markers + ≥1 reference/CI line artist."""
    n_scatter_pts = 0
    n_lines = 0
    for a in fig.axes:
        for c in a.collections:
            if type(c).__name__ == "PathCollection":
                try:
                    n_scatter_pts += len(c.get_offsets())
                except Exception:
                    n_scatter_pts += 1
        n_lines += len(a.get_lines())
    assert n_scatter_pts >= 3, (
        f"{entry.full_name}: forest needs ≥3 estimate markers "
        f"(got {n_scatter_pts})."
    )
    assert n_lines >= 1, (
        f"{entry.full_name}: forest needs ≥1 reference/CI line "
        f"(got {n_lines})."
    )
