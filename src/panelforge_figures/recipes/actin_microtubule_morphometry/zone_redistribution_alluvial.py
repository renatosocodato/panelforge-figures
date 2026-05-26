"""Zone redistribution alluvial — flow of territory fractions across groups.

Each input row is (group, zone, fraction). The recipe renders a stacked
horizontal bar where each group's bar is partitioned by zone fraction,
with bezier-curve flows connecting matching zones across adjacent groups.
"""

from __future__ import annotations

from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class ZoneRedistributionInput(RecipeContract):
    fractions_by_group: dict[str, dict[str, float]] = Field(
        description="group → {zone: fraction}; fractions sum ≤ 1 per group"
    )
    zone_order: list[str] | None = Field(
        default=None, description="Optional explicit ordering of zone keys (left-to-right band)"
    )
    title: str = "Zone redistribution"


def _demo() -> ZoneRedistributionInput:
    return ZoneRedistributionInput(
        fractions_by_group={
            "WT": {"contact": 0.02, "actin_exclusive": 0.07, "mt_exclusive": 0.19,
                   "desert": 0.72, "contact_peak": 0.06},
            "LI": {"contact": 0.08, "actin_exclusive": 0.10, "mt_exclusive": 0.23,
                   "desert": 0.58, "contact_peak": 0.14},
        },
        title="Territory zone redistribution WT to LI",
    )


_META = RecipeMetadata(
    name="zone_redistribution_alluvial",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.conceptual,
    answers_question="How do territory zone fractions redistribute across groups?",
    required_fields=("fractions_by_group",),
    optional_fields=("zone_order", "title"),
    file_format_hints=("csv", "json"),
    alternatives_in_modality=("territory_contact_network_overlay",),
)


_ZONE_COLORS = {
    "contact":         "#8e7c3f",
    "actin_exclusive": "#5b8aa4",
    "mt_exclusive":    "#a76343",
    "desert":          "#bcbcbc",
    "contact_peak":    "#3e6e7d",
}


@register_recipe(metadata=_META, contract=ZoneRedistributionInput, demo_contract=_demo)
def render(contract: ZoneRedistributionInput, ax=None, **_):
    import matplotlib.patches as mpatches
    import matplotlib.pyplot as plt
    import numpy as np

    if ax is None:
        _, ax = plt.subplots(figsize=(8.5, 4.5))
    AESTHETIC.apply_to_ax(ax)

    groups = list(contract.fractions_by_group.keys())
    zone_order = contract.zone_order or sorted({
        z for d in contract.fractions_by_group.values() for z in d
    })

    bar_w = 0.18
    x_positions = np.linspace(0.1, 0.9, len(groups))

    # Per-group stacked bars
    bar_segments = {}  # (group, zone) → (y0, y1)
    for gi, g in enumerate(groups):
        x0 = x_positions[gi] - bar_w / 2
        y_cursor = 0.0
        for z in zone_order:
            v = contract.fractions_by_group[g].get(z, 0.0)
            color = _ZONE_COLORS.get(z, "#bbb")
            ax.add_patch(mpatches.Rectangle((x0, y_cursor), bar_w, v,
                                             facecolor=color, edgecolor="white",
                                             linewidth=0.8))
            ax.text(x_positions[gi], y_cursor + v / 2, f"{v:.2f}",
                    ha="center", va="center", fontsize=8.4,
                    color="white" if v > 0.10 else "#444")
            bar_segments[(g, z)] = (y_cursor, y_cursor + v)
            y_cursor += v

    # Connection flows between adjacent groups
    for gi in range(len(groups) - 1):
        ga, gb = groups[gi], groups[gi + 1]
        xa = x_positions[gi] + bar_w / 2
        xb = x_positions[gi + 1] - bar_w / 2
        for z in zone_order:
            ya0, ya1 = bar_segments[(ga, z)]
            yb0, yb1 = bar_segments[(gb, z)]
            color = _ZONE_COLORS.get(z, "#bbb")
            # Bezier-ish polygon
            mid = (xa + xb) / 2
            verts = [(xa, ya0), (mid, ya0), (mid, yb0), (xb, yb0),
                     (xb, yb1), (mid, yb1), (mid, ya1), (xa, ya1)]
            ax.add_patch(mpatches.Polygon(verts, closed=True,
                                           facecolor=color, alpha=0.22,
                                           edgecolor="none"))

    # Group labels
    for gi, g in enumerate(groups):
        ax.text(x_positions[gi], -0.04, g,
                ha="center", va="top", fontsize=9.6, fontweight="bold")

    # Zone legend
    legend_handles = [mpatches.Patch(color=_ZONE_COLORS.get(z, "#bbb"), label=z)
                      for z in zone_order]
    ax.legend(handles=legend_handles, fontsize=8.4, frameon=False,
              loc="center left", bbox_to_anchor=(1.0, 0.5))

    ax.set_xlim(0, 1)
    ax.set_ylim(-0.08, 1.04)
    ax.axis("off")
    ax.set_title(contract.title, fontsize=9.6, color="#2c3e50", pad=6)
    return ax
