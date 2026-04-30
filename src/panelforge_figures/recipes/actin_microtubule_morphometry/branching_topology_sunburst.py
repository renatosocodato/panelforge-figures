"""Branching-topology sunburst — nested-ring donut of branch-depth hierarchy by condition."""

from __future__ import annotations

import matplotlib.patches as mpatches
import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class BranchingSunburstInput(RecipeContract):
    depth_counts_by_condition: dict[str, dict[int, int]] = Field(
        ..., description="condition → {depth_level: count}"
    )
    max_depth: int = 4
    title: str = "Branching-topology sunburst"


def _demo() -> BranchingSunburstInput:
    # Three conditions with different depth profiles.
    return BranchingSunburstInput(
        depth_counts_by_condition={
            "control":  {0: 60, 1: 100, 2: 72, 3: 36, 4: 12},
            "mutant":   {0: 60, 1: 62,  2: 22, 3: 8,  4: 2},
            "rescue":   {0: 60, 1: 88,  2: 54, 3: 24, 4: 6},
        },
        max_depth=4,
    )


_META = RecipeMetadata(
    name="branching_topology_sunburst",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.matrix,
    answers_question=(
        "How does the skeleton's branching hierarchy (depth 0/1/2/3+) "
        "split by condition, in a single nested-ring view?"
    ),
    required_fields=("depth_counts_by_condition",),
    optional_fields=("max_depth", "title"),
    file_format_hints=("csv", "yaml"),
    alternatives_in_modality=(
        "branch_angle_distribution",
        "topology_ternary_simplex",
    ),
)


@register_recipe(
    metadata=_META,
    contract=BranchingSunburstInput,
    demo_contract=_demo,
)
def render(contract: BranchingSunburstInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 4.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    conditions = list(contract.depth_counts_by_condition.keys())
    max_depth = contract.max_depth
    n_conds = len(conditions)
    # Sunburst: one angular wedge per condition, each subdivided radially
    # into (max_depth + 1) nested rings coloured by depth-level fraction.
    wedge_angle = 360.0 / max(n_conds, 1)

    # Depth-level colours (viridis-lite).
    import matplotlib as mpl
    depth_cmap = mpl.colormaps[AESTHETIC.continuous_cmap]
    depth_colors = [depth_cmap(f / max(max_depth, 1))
                    for f in range(max_depth + 1)]

    r_outer_base = 1.0
    ring_width = 0.18
    total_radius = r_outer_base + (max_depth + 1) * ring_width

    for ci, cond in enumerate(conditions):
        theta_start = ci * wedge_angle - 90.0
        theta_end = (ci + 1) * wedge_angle - 90.0
        depth_counts = contract.depth_counts_by_condition[cond]
        total = sum(depth_counts.values()) or 1
        r_in = r_outer_base
        for d in range(max_depth + 1):
            fraction = depth_counts.get(d, 0) / total
            # Full ring width, alpha by fraction (so you see the emphasis).
            alpha = 0.30 + 0.65 * fraction
            r_out = r_in + ring_width
            w = mpatches.Wedge(
                (0.0, 0.0), r_out, theta_start, theta_end,
                width=ring_width,
                facecolor=depth_colors[d], edgecolor="white", linewidth=0.6,
                alpha=alpha, zorder=3,
            )
            ax.add_patch(w)
            r_in = r_out

        # Condition label at wedge centroid (outside the outer ring).
        mid_theta = np.deg2rad(0.5 * (theta_start + theta_end))
        r_label = total_radius + 0.18
        cond_color = palette[ci % len(palette.colors)]
        ax.text(r_label * np.cos(mid_theta), r_label * np.sin(mid_theta),
                cond, ha="center", va="center",
                fontsize=7.4, color=cond_color, fontweight="bold")

    # Centre summary: total n per condition with %-at-depth-≥2.
    summary_parts = []
    for cond in conditions:
        dc = contract.depth_counts_by_condition[cond]
        total = sum(dc.values())
        deep = sum(v for d, v in dc.items() if d >= 2)
        pct = 100 * deep / max(total, 1)
        summary_parts.append(f"{cond}: {total}n, {smart_fmt(pct)}% deep")
    ax.text(0, 0, "depth\nhierarchy",
            ha="center", va="center",
            fontsize=7.4, color="#111111", fontweight="bold")
    ax.figure.text(
        0.5, 0.02, "  ·  ".join(summary_parts),
        ha="center", va="bottom", fontsize=6.2, color="#333333",
    )

    # Depth colorbar legend — proxy horizontal strip. Wider swatch spacing
    # so the "d=N" labels don't run together.
    swatch_w = 0.24
    swatch_h = 0.10
    gap = 0.30
    legend_x0 = -total_radius - 0.40
    legend_y = -total_radius - 0.22
    for d in range(max_depth + 1):
        x = legend_x0 + d * gap
        ax.add_patch(mpatches.Rectangle(
            (x, legend_y), swatch_w, swatch_h,
            facecolor=depth_colors[d], edgecolor="white", linewidth=0.3,
        ))
        ax.text(x + swatch_w / 2, legend_y - 0.03,
                f" d={d} ", ha="center", va="top",
                fontsize=5.6, color="#333333")

    ax.set_xlim(-total_radius - 0.7, total_radius + 0.7)
    ax.set_ylim(-total_radius - 0.6, total_radius + 0.45)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    return ax
