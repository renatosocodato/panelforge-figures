"""Instantaneous-speed distribution per morphological state (split violin).

Plots the distribution of instantaneous speed (μm/min) for cells in
each morphological state, with median / quartile overlays and Ns.

Distinct from `cell_shape_descriptors_by_state` (shape, not speed)
and `migration_rose_diagram` (angle distribution, not speed).
"""

from __future__ import annotations

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


class VelocityByStateInput(RecipeContract):
    states: list[str] = Field(..., min_length=2)
    speed_by_state: dict[str, list[float]] = Field(
        ..., description="state → per-step instantaneous speed (μm/min)"
    )
    speed_label: str = "speed (μm/min)"
    title: str = "Instantaneous speed by state"


def _demo() -> VelocityByStateInput:
    rng = np.random.default_rng(1237)
    states = ["homeostatic", "surveillant", "activated"]
    speeds = {
        "homeostatic": rng.gamma(2.0, 0.6, 300).tolist(),
        "surveillant": rng.gamma(3.0, 1.0, 320).tolist(),
        "activated":   rng.gamma(3.5, 1.8, 280).tolist(),
    }
    return VelocityByStateInput(states=states, speed_by_state=speeds)


_META = RecipeMetadata(
    name="velocity_distribution_by_state",
    modality="intravital_imaging",
    family=RecipeFamily.split_violin,
    answers_question=(
        "For each morphological state, how do the instantaneous-speed "
        "distributions compare?"
    ),
    required_fields=("states", "speed_by_state"),
    optional_fields=("speed_label", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=(
        "cell_shape_descriptors_by_state", "migration_rose_diagram",
    ),
)


@register_recipe(
    metadata=_META,
    contract=VelocityByStateInput,
    demo_contract=_demo,
)
def render(contract: VelocityByStateInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    states = contract.states
    data = [np.asarray(contract.speed_by_state.get(s, []), float)
            for s in states]
    positions = list(range(len(states)))

    parts = ax.violinplot(data, positions=positions, widths=0.72,
                          showmeans=False, showmedians=False, showextrema=False)
    for i, pc in enumerate(parts["bodies"]):
        color = (palette.pick(states[i]) if states[i] in palette.semantic
                 else palette[i])
        pc.set_facecolor(color)
        pc.set_edgecolor("#333333")
        pc.set_alpha(0.55)
        pc.set_linewidth(0.6)

    for pos, vals in zip(positions, data):
        if vals.size < 4:
            continue
        q1, med, q3 = np.quantile(vals, [0.25, 0.5, 0.75])
        ax.plot([pos, pos], [q1, q3], color="black",
                lw=3.0, solid_capstyle="butt", zorder=4)
        ax.scatter([pos], [med], s=36, facecolor="white",
                   edgecolor="black", linewidth=1.0, zorder=5)

    # Median + N labels below category.
    for pos, name, vals in zip(positions, states, data):
        if vals.size:
            med = float(np.median(vals))
            ax.text(pos + 0.06, med, smart_fmt(med),
                    ha="left", va="center", fontsize=6.2, color="#222222")
        ax.text(pos, -0.08, f"N = {vals.size}",
                transform=ax.get_xaxis_transform(),
                ha="center", va="top", fontsize=6.2, color="#666666")

    ax.set_xticks(positions)
    ax.set_xticklabels(states, fontsize=7.2)
    ax.set_ylabel(contract.speed_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
