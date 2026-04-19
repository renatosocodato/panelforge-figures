"""Total process length per cell — split violin by sex × genotype."""

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


class ProcessLengthBySexInput(RecipeContract):
    process_length_by_group: dict[str, list[float]] = Field(
        ..., description="group key (F_WT / M_WT / F_KO / M_KO) → per-cell total length (µm)"
    )
    sex_x_genotype_order: list[str] = Field(
        default_factory=lambda: ["F_WT", "M_WT", "F_KO", "M_KO"],
        description="ordered group keys matching the palette convention",
    )
    title: str = "Total process length by sex × genotype"


def _demo() -> ProcessLengthBySexInput:
    rng = np.random.default_rng(801)
    # WT cells long, KO shorter; modest sex effect superimposed.
    return ProcessLengthBySexInput(
        process_length_by_group={
            "F_WT": rng.lognormal(4.4, 0.28, 64).tolist(),
            "M_WT": rng.lognormal(4.35, 0.32, 60).tolist(),
            "F_KO": rng.lognormal(3.95, 0.30, 58).tolist(),
            "M_KO": rng.lognormal(4.05, 0.26, 62).tolist(),
        },
    )


_META = RecipeMetadata(
    name="process_length_distribution_by_sex",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.split_violin,
    answers_question=(
        "How does total per-cell process length distribute by sex × genotype?"
    ),
    required_fields=("process_length_by_group",),
    optional_fields=("sex_x_genotype_order", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("cell_body_area_distribution",),
)


@register_recipe(
    metadata=_META,
    contract=ProcessLengthBySexInput,
    demo_contract=_demo,
)
def render(contract: ProcessLengthBySexInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette("sex_x_genotype")

    groups = [g for g in contract.sex_x_genotype_order
              if g in contract.process_length_by_group]
    positions = list(range(len(groups)))
    data = [np.asarray(contract.process_length_by_group[g], float) for g in groups]

    parts = ax.violinplot(data, positions=positions, widths=0.78,
                          showmeans=False, showmedians=False, showextrema=False)
    for i, pc in enumerate(parts["bodies"]):
        color = (palette.pick(groups[i]) if groups[i] in palette.semantic
                 else palette[i % len(palette.colors)])
        pc.set_facecolor(color)
        pc.set_edgecolor("#333333")
        pc.set_alpha(0.55)

    rng = np.random.default_rng(803)
    for pos, vals, g in zip(positions, data, groups):
        color = (palette.pick(g) if g in palette.semantic else palette[0])
        jitter = rng.uniform(-0.14, 0.14, vals.size)
        ax.scatter(pos + jitter, vals, s=7, color=color, alpha=0.55,
                   edgecolor="white", linewidth=0.25, zorder=3)
        if vals.size >= 4:
            q1, med, q3 = np.quantile(vals, [0.25, 0.5, 0.75])
            ax.plot([pos, pos], [q1, q3], color="black",
                    lw=3.0, solid_capstyle="butt", zorder=4)
            ax.scatter([pos], [med], s=38, facecolor="white",
                       edgecolor="black", linewidth=1.0, zorder=5)
            ax.text(pos + 0.18, med, smart_fmt(float(med)),
                    ha="left", va="center", fontsize=6.2, color="#111111")

    # Per-group N annotations.
    for pos, vals in zip(positions, data):
        ax.text(pos, -0.08, f"N = {vals.size}",
                transform=ax.get_xaxis_transform(),
                ha="center", va="top", fontsize=6.2, color="#666666")

    # Faint vertical divider between sex columns.
    if len(groups) == 4:
        ax.axvline(1.5, color="#CCCCCC", lw=0.5, ls=":", zorder=0)

    ax.set_xticks(positions)
    ax.set_xticklabels(groups, fontsize=7.0)
    ax.set_ylabel(r"total process length ($\mu$m)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
