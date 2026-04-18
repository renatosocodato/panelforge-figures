"""Quality rules for `omics_differential` families: volcano."""

from __future__ import annotations


def assert_volcano_ok(fig, entry):
    """volcano — ≥1 scatter (many genes) + ≥1 threshold line + ≥2 points."""
    scatter_pts = 0
    line_count = 0
    for a in fig.axes:
        for c in a.collections:
            if type(c).__name__ == "PathCollection":
                try:
                    scatter_pts += len(c.get_offsets())
                except (AttributeError, ValueError):
                    scatter_pts += 1
        line_count += len(a.get_lines())
    assert scatter_pts >= 10, (
        f"{entry.full_name}: volcano needs ≥10 scatter points "
        f"(got {scatter_pts})."
    )
    assert line_count >= 1, (
        f"{entry.full_name}: volcano needs ≥1 threshold line "
        f"(got {line_count})."
    )
