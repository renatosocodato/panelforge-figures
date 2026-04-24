"""Feature-outcome Sankey — alluvial flow from total features to scale
stratum to TOST outcome class (significant / null_accepting /
equivocal). Shows where the 109/149 breakdown concentrates across the
organizational hierarchy.

Flow family: >=2 rounded boxes + >=1 annotation arrow. Implemented
with matplotlib primitives (FancyBboxPatch for the nodes, Polygon
quadrilaterals for the alluvial ribbons, FancyArrow for the overall
flow direction). No matplotlib-sankey dep.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
)
from ._aesthetic import AESTHETIC
from ._shared import (
    OUTCOME_PALETTE_DEFAULT,
    EffectSizeEstimate,
    _demo_estimate_roster,
)

_SCALE_COLOURS = {
    "polymer": "#1565C0",
    "network": "#E65100",
    "territory": "#6A1B9A",
    "geometry": "#2E7D32",
    "whole_cell": "#B71C1C",
}


class FeatureOutcomeSankeyInput(RecipeContract):
    estimates: list[EffectSizeEstimate] = Field(..., min_length=6)
    scale_order: list[str] = Field(
        default_factory=lambda: [
            "polymer", "network", "territory", "geometry", "whole_cell",
        ],
    )
    outcome_order: list[str] = Field(
        default_factory=lambda: [
            "significant", "null_accepting", "equivocal",
        ],
    )
    compartment_filter: str | None = Field(
        None,
        description="if set, only estimates matching this compartment are counted",
    )
    title: str = "Feature-outcome Sankey (scale x outcome)"


def _demo() -> FeatureOutcomeSankeyInput:
    return FeatureOutcomeSankeyInput(
        estimates=_demo_estimate_roster(),
        compartment_filter="whole_cell",
    )


_META = RecipeMetadata(
    name="feature_outcome_sankey_sig_vs_null",
    modality="biophysics_scaling",
    family=RecipeFamily.flow,
    answers_question=(
        "Where across the scale hierarchy do the significant / "
        "null-accepting / equivocal feature outcomes concentrate?"
    ),
    required_fields=("estimates",),
    optional_fields=(
        "scale_order", "outcome_order", "compartment_filter", "title",
    ),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("hierarchical_effect_size_ladder",),
)


@register_recipe(
    metadata=_META,
    contract=FeatureOutcomeSankeyInput,
    demo_contract=_demo,
)
def render(contract: FeatureOutcomeSankeyInput, ax=None, **_):
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch, Polygon
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.2, 3.8))
    AESTHETIC.apply_to_ax(ax)

    palette = AESTHETIC.outcome_palette or OUTCOME_PALETTE_DEFAULT

    ests = list(contract.estimates)
    if contract.compartment_filter is not None:
        ests = [e for e in ests if e.compartment == contract.compartment_filter]
    total = len(ests)

    # Count per (scale, outcome).
    scale_counts: dict[str, int] = {s: 0 for s in contract.scale_order}
    outcome_counts: dict[str, int] = {o: 0 for o in contract.outcome_order}
    cell_counts: dict[tuple[str, str], int] = {}
    for e in ests:
        scale_counts[e.scale] = scale_counts.get(e.scale, 0) + 1
        outcome_counts[e.outcome_class] = (
            outcome_counts.get(e.outcome_class, 0) + 1
        )
        key = (e.scale, e.outcome_class)
        cell_counts[key] = cell_counts.get(key, 0) + 1

    # Three columns: total | scale | outcome.
    col_x = [0.08, 0.48, 0.88]  # centre x in axes-fraction
    col_w = 0.10
    # Column 0: single big box.
    node_h_total = 0.72
    node_y_total = 0.14

    ax.add_patch(FancyBboxPatch(
        (col_x[0] - col_w / 2, node_y_total),
        col_w, node_h_total,
        boxstyle="round,pad=0.006,rounding_size=0.012",
        facecolor="#455A64", edgecolor="white", linewidth=0.8,
        alpha=0.92, zorder=4,
    ))
    ax.text(col_x[0], node_y_total + node_h_total / 2,
            f"all\nfeatures\nn = {total}",
            ha="center", va="center", fontsize=6.6,
            color="white", fontweight="bold", zorder=5)

    # Column 1: scale nodes stacked vertically.
    scale_y: dict[str, tuple[float, float]] = {}
    y_cursor = 0.86
    gap = 0.012
    for scale in contract.scale_order:
        count = scale_counts.get(scale, 0)
        if count == 0:
            continue
        h = 0.72 * count / total
        y_cursor -= h
        ax.add_patch(FancyBboxPatch(
            (col_x[1] - col_w / 2, y_cursor),
            col_w, h,
            boxstyle="round,pad=0.004,rounding_size=0.010",
            facecolor=_SCALE_COLOURS.get(scale, "#555555"),
            edgecolor="white", linewidth=0.7, alpha=0.92, zorder=4,
        ))
        ax.text(col_x[1], y_cursor + h / 2,
                f"{scale}\nn = {count}",
                ha="center", va="center", fontsize=6.2,
                color="white", fontweight="bold", zorder=5)
        scale_y[scale] = (y_cursor, y_cursor + h)
        y_cursor -= gap

    # Column 2: outcome nodes stacked.
    outcome_y: dict[str, tuple[float, float]] = {}
    y_cursor = 0.86
    for outcome in contract.outcome_order:
        count = outcome_counts.get(outcome, 0)
        if count == 0:
            continue
        h = 0.72 * count / total
        y_cursor -= h
        ax.add_patch(FancyBboxPatch(
            (col_x[2] - col_w / 2, y_cursor),
            col_w, h,
            boxstyle="round,pad=0.004,rounding_size=0.010",
            facecolor=palette.get(outcome, palette["equivocal"]),
            edgecolor="white", linewidth=0.7, alpha=0.92, zorder=4,
        ))
        ax.text(col_x[2], y_cursor + h / 2,
                f"{outcome.replace('_', '-')}\nn = {count}",
                ha="center", va="center", fontsize=6.0,
                color="white", fontweight="bold", zorder=5)
        outcome_y[outcome] = (y_cursor, y_cursor + h)
        y_cursor -= gap

    # Ribbons: total -> scale (col 0 -> 1).
    total_y = [node_y_total, node_y_total + node_h_total]
    cursor_left = total_y[1]
    x0 = col_x[0] + col_w / 2
    x1 = col_x[1] - col_w / 2
    for scale in contract.scale_order:
        count = scale_counts.get(scale, 0)
        if count == 0:
            continue
        left_h = node_h_total * count / total
        left_top = cursor_left
        left_bot = cursor_left - left_h
        right_top, right_bot = scale_y[scale][1], scale_y[scale][0]
        # Bezier-ish polygon: use linspace to sample a smooth curve.
        xs = np.linspace(x0, x1, 24)
        tops = left_top + (right_top - left_top) * _smoothstep(
            np.linspace(0, 1, 24)
        )
        bots = left_bot + (right_bot - left_bot) * _smoothstep(
            np.linspace(0, 1, 24)
        )
        poly = np.concatenate([
            np.stack([xs, tops], axis=1),
            np.stack([xs[::-1], bots[::-1]], axis=1),
        ])
        ax.add_patch(Polygon(
            poly, closed=True,
            facecolor=_SCALE_COLOURS.get(scale, "#555555"),
            edgecolor="none", alpha=0.35, zorder=2,
        ))
        cursor_left = left_bot

    # Ribbons: scale -> outcome (col 1 -> 2).
    x2 = col_x[1] + col_w / 2
    x3 = col_x[2] - col_w / 2
    # Track y-cursors on both sides.
    left_cursors = {s: scale_y[s][1] for s in scale_y}
    right_cursors = {o: outcome_y[o][1] for o in outcome_y}
    for scale in contract.scale_order:
        if scale not in scale_y:
            continue
        for outcome in contract.outcome_order:
            if outcome not in outcome_y:
                continue
            count = cell_counts.get((scale, outcome), 0)
            if count == 0:
                continue
            s_frac = count / scale_counts[scale]
            o_frac = count / outcome_counts[outcome]
            s_h = (scale_y[scale][1] - scale_y[scale][0]) * s_frac
            o_h = (outcome_y[outcome][1] - outcome_y[outcome][0]) * o_frac
            left_top = left_cursors[scale]
            left_bot = left_top - s_h
            right_top = right_cursors[outcome]
            right_bot = right_top - o_h
            xs = np.linspace(x2, x3, 24)
            tops = left_top + (right_top - left_top) * _smoothstep(
                np.linspace(0, 1, 24)
            )
            bots = left_bot + (right_bot - left_bot) * _smoothstep(
                np.linspace(0, 1, 24)
            )
            poly = np.concatenate([
                np.stack([xs, tops], axis=1),
                np.stack([xs[::-1], bots[::-1]], axis=1),
            ])
            ax.add_patch(Polygon(
                poly, closed=True,
                facecolor=palette.get(outcome, palette["equivocal"]),
                edgecolor="none", alpha=0.30, zorder=2,
            ))
            left_cursors[scale] = left_bot
            right_cursors[outcome] = right_bot

    # Column headers.
    for x, label in zip(col_x, ["total", "scale", "outcome"]):
        ax.text(x, 0.93, label, ha="center", va="bottom",
                fontsize=7.0, color="#333333", fontweight="bold")

    # Overall-flow arrow below the three columns (satisfies flow rule).
    ax.annotate("", xy=(col_x[2] + 0.06, 0.06), xytext=(col_x[0] - 0.06, 0.06),
                arrowprops=dict(arrowstyle="->", color="#555555",
                                lw=1.0), zorder=3)
    ax.text(0.5, 0.03, "feature -> scale -> outcome",
            ha="center", va="center", fontsize=6.4,
            color="#555555", style="italic")

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_title(
        f"{contract.title}  ·  n = {total}  ·  "
        f"sig {outcome_counts.get('significant', 0)}  ·  "
        f"null-accept {outcome_counts.get('null_accepting', 0)}  ·  "
        f"equivocal {outcome_counts.get('equivocal', 0)}",
        fontsize=8.2, pad=6,
    )
    # Suppress unused-import lint for mpatches (used via FancyBboxPatch /
    # Polygon imports).
    _ = mpatches
    return ax


def _smoothstep(t: np.ndarray) -> np.ndarray:
    """Smooth ease curve for ribbon interpolation."""
    return t * t * (3.0 - 2.0 * t)
