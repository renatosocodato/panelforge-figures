"""Cost-by-work-package stacked horizontal bars — budget distribution
across WPs by cost category (personnel, consumables, travel, equipment,
other).

Ladder family: ≥3 horizontal bars per WP.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class CostByWPInput(RecipeContract):
    wp_names: list[str] = Field(..., min_length=3)
    category_names: list[str] = Field(..., min_length=2)
    cost_matrix: list[list[float]] = Field(
        ..., description="n_wp × n_categories matrix of costs (EUR / USD)"
    )
    currency: str = "EUR"
    title: str = "Cost by work package"


def _demo() -> CostByWPInput:
    return CostByWPInput(
        wp_names=["WP1 cohorts", "WP2 computation",
                  "WP3 in vivo", "WP4 translation", "WP5 coord"],
        category_names=["personnel", "consumables", "equipment",
                        "travel", "other"],
        cost_matrix=[
            [180000,  24000,  30000,  6000,  4000],
            [230000,  12000,   8000,  6000,  3000],
            [160000,  52000,  22000,  4000,  5000],
            [140000,  18000,   6000, 12000,  7000],
            [ 80000,   4000,   2000,  6000, 14000],
        ],
        currency="EUR",
    )


_META = RecipeMetadata(
    name="cost_by_work_package_bar",
    modality="grant_and_conceptual",
    family=RecipeFamily.ladder,
    answers_question=(
        "How is the proposal budget distributed across work packages, "
        "broken down by cost category?"
    ),
    required_fields=("wp_names", "category_names", "cost_matrix"),
    optional_fields=("currency", "title"),
    file_format_hints=("csv", "yaml"),
    alternatives_in_modality=("timeline_gantt_with_milestones",),
)


@register_recipe(
    metadata=_META,
    contract=CostByWPInput,
    demo_contract=_demo,
)
def render(contract: CostByWPInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.4))
    AESTHETIC.apply_to_ax(ax)

    wps = contract.wp_names
    cats = contract.category_names
    M = np.asarray(contract.cost_matrix, float)   # n_wp × n_cat

    y = np.arange(len(wps))
    # Category colours — muted palette.
    cat_colors = ["#455A64", "#78909C", "#FFB300", "#C2185B", "#00796B"]
    totals = M.sum(axis=1)
    grand_total = float(totals.sum())

    # Horizontal stacked bars.
    left = np.zeros(len(wps))
    for ci, cat in enumerate(cats):
        col = M[:, ci]
        ax.barh(y, col, left=left,
                color=cat_colors[ci % len(cat_colors)],
                edgecolor="white", linewidth=0.5,
                alpha=0.92, zorder=3,
                label=cat)
        left += col

    # Per-WP total label at right.
    for yi, t in zip(y, totals):
        ax.text(t + grand_total * 0.005, yi,
                f"{smart_fmt(t / 1000)}k",
                ha="left", va="center", fontsize=6.8,
                color="#333333", zorder=5)

    ax.set_yticks(y)
    ax.set_yticklabels(wps, fontsize=7.2)
    ax.invert_yaxis()
    ax.set_xlabel(f"cost ({contract.currency})")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              bbox_to_anchor=(1.0, -0.08),
              ncols=min(len(cats), 5), handlelength=1.0,
              columnspacing=1.2)

    # Grand-total footer.
    ax.text(0.02, 0.97,
            f"total: {smart_fmt(grand_total / 1000)}k {contract.currency}",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.8, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)

    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    return ax
