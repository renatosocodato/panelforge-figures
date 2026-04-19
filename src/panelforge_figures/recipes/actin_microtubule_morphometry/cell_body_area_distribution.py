"""Soma area distribution per condition — violin with median + N annotations."""

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


class CellBodyAreaInput(RecipeContract):
    soma_areas_by_condition: dict[str, list[float]] = Field(
        ..., description="condition → per-cell soma area (µm²)"
    )
    title: str = "Cell-body (soma) area"


def _demo() -> CellBodyAreaInput:
    rng = np.random.default_rng(711)
    return CellBodyAreaInput(
        soma_areas_by_condition={
            "control": rng.lognormal(5.5, 0.32, 64).tolist(),
            "mutant":  rng.lognormal(5.9, 0.30, 58).tolist(),
            "rescue":  rng.lognormal(5.6, 0.28, 60).tolist(),
        },
    )


_META = RecipeMetadata(
    name="cell_body_area_distribution",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.split_violin,
    answers_question=(
        "How does the per-cell soma area distribute across conditions?"
    ),
    required_fields=("soma_areas_by_condition",),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("cortical_thickness_by_region",),
)


@register_recipe(
    metadata=_META,
    contract=CellBodyAreaInput,
    demo_contract=_demo,
)
def render(contract: CellBodyAreaInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    conditions = list(contract.soma_areas_by_condition.keys())
    positions = list(range(len(conditions)))
    data = [np.asarray(contract.soma_areas_by_condition[c], float) for c in conditions]

    parts = ax.violinplot(data, positions=positions, widths=0.78,
                          showmeans=False, showmedians=False, showextrema=False)
    for i, pc in enumerate(parts["bodies"]):
        color = palette[i % len(palette.colors)]
        pc.set_facecolor(color)
        pc.set_edgecolor("#333333")
        pc.set_alpha(0.55)

    rng = np.random.default_rng(713)
    for pos, vals, color_idx in zip(positions, data, range(len(conditions))):
        color = palette[color_idx % len(palette.colors)]
        jitter = rng.uniform(-0.14, 0.14, vals.size)
        ax.scatter(pos + jitter, vals, s=8, color=color, alpha=0.5,
                   edgecolor="white", linewidth=0.25, zorder=3)
        if vals.size >= 4:
            q1, med, q3 = np.quantile(vals, [0.25, 0.5, 0.75])
            ax.plot([pos, pos], [q1, q3], color="black",
                    lw=3.0, solid_capstyle="butt", zorder=4)
            ax.scatter([pos], [med], s=40, facecolor="white",
                       edgecolor="black", linewidth=1.0, zorder=5)
            ax.text(pos + 0.18, med, f"{smart_fmt(float(med))}",
                    ha="left", va="center", fontsize=6.4, color="#111111")

    # N labels under each condition.
    for pos, vals in zip(positions, data):
        ax.text(pos, -0.08, f"N = {vals.size}",
                transform=ax.get_xaxis_transform(),
                ha="center", va="top", fontsize=6.2, color="#666666")

    ax.set_xticks(positions)
    ax.set_xticklabels(conditions, fontsize=7.0)
    ax.set_ylabel(r"soma area ($\mu$m$^2$)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
