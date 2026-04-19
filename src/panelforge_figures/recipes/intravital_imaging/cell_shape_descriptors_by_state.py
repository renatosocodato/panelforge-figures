"""Cell-shape descriptors by state — violins of circularity / elongation per cell state."""

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


class ShapeByStateInput(RecipeContract):
    states: list[str] = Field(..., min_length=2)
    circularity_by_state: dict[str, list[float]] = Field(...)
    title: str = "Cell shape descriptors"


def _demo() -> ShapeByStateInput:
    rng = np.random.default_rng(469)
    states = ["homeostatic", "surveillant", "activated"]
    circ = {
        "homeostatic": rng.beta(6, 2, 120).tolist(),   # round
        "surveillant": rng.beta(3, 3, 110).tolist(),   # intermediate
        "activated":   rng.beta(2, 5, 130).tolist(),   # elongated
    }
    return ShapeByStateInput(
        states=states,
        circularity_by_state=circ,
    )


_META = RecipeMetadata(
    name="cell_shape_descriptors_by_state",
    modality="intravital_imaging",
    family=RecipeFamily.split_violin,
    answers_question="How do cell-shape descriptors (circularity / elongation) differ across morphological states?",
    required_fields=("states", "circularity_by_state"),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("migration_rose_diagram",),
)


@register_recipe(metadata=_META, contract=ShapeByStateInput, demo_contract=_demo)
def render(contract: ShapeByStateInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    states = contract.states
    data = [np.array(contract.circularity_by_state.get(s, []), float)
            for s in states]
    positions = list(range(len(states)))

    parts = ax.violinplot(data, positions=positions, widths=0.72,
                          showmeans=False, showmedians=False, showextrema=False)
    for i, pc in enumerate(parts["bodies"]):
        color = (palette.pick(states[i])
                 if states[i] in palette.semantic else palette[i])
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

    # N labels.
    for pos, vals in zip(positions, data):
        ax.text(pos, -0.08, f"N = {vals.size}",
                transform=ax.get_xaxis_transform(),
                ha="center", va="top", fontsize=6.2, color="#666666")
        # Median label.
        if vals.size:
            med = float(np.median(vals))
            ax.text(pos + 0.05, med, f"med {smart_fmt(med)}",
                    ha="left", va="center", fontsize=6.0, color="#222222")

    ax.set_xticks(positions)
    ax.set_xticklabels(states, fontsize=7.0)
    ax.set_ylabel("circularity (1 = perfect circle)")
    ax.set_ylim(0, 1.05)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
