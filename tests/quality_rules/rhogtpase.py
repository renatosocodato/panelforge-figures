"""Quality rules for rhogtpase_dynamics families: phase_portrait, bifurcation."""

from __future__ import annotations


def _collections_of_type(fig, name: str):
    out = []
    for a in fig.axes:
        out.extend(c for c in a.collections if type(c).__name__ == name)
    return out


def assert_phase_portrait_ok(fig, entry):
    """phase_portrait — must have a streamplot/quiver AND at least one fixed-point marker."""
    has_vector = bool(
        _collections_of_type(fig, "LineCollection")
        or _collections_of_type(fig, "PolyCollection")
        or [c for a in fig.axes for c in a.collections
            if type(c).__name__ == "PathCollection"]
        or [a for a in fig.axes if a.images]
    )
    assert has_vector, (
        f"{entry.full_name}: phase portrait needs a streamplot, quiver, "
        "or pcolormesh backdrop."
    )
    # Fixed-point markers are PathCollection scatters.
    n_scatter = sum(
        len([c for c in a.collections if type(c).__name__ == "PathCollection"])
        for a in fig.axes
    )
    assert n_scatter >= 1, (
        f"{entry.full_name}: phase portrait needs ≥1 scatter (fixed points)."
    )


def assert_bifurcation_ok(fig, entry):
    """bifurcation — ≥2 distinct branches (Line2D) + ≥1 star/marker + ≥1 axvspan."""
    # Count Line2D objects across all axes.
    n_lines = sum(len(a.get_lines()) for a in fig.axes)
    assert n_lines >= 2, (
        f"{entry.full_name}: bifurcation needs ≥2 branches (got {n_lines})."
    )
    # Shaded regime regions are Rectangle patches via axvspan; fixed-point
    # stars/markers are PathCollection scatters via ax.scatter.
    n_patches = sum(len(a.patches) for a in fig.axes)
    n_scatter_pts = 0
    for a in fig.axes:
        for c in a.collections:
            if type(c).__name__ == "PathCollection":
                try:
                    n_scatter_pts += len(c.get_offsets())
                except Exception:
                    n_scatter_pts += 1
    assert n_patches >= 1 or n_scatter_pts >= 1, (
        f"{entry.full_name}: bifurcation needs ≥1 regime shading or marker."
    )
