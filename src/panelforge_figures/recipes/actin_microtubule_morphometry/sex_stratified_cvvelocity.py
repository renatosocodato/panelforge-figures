"""Coefficient of variation of instantaneous velocity — sex × genotype split violin."""

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


class CVVelocityInput(RecipeContract):
    cv_velocity_by_group: dict[str, list[float]] = Field(
        ..., description="group key → per-cell CV of instantaneous velocity"
    )
    sex_x_genotype_order: list[str] = Field(
        default_factory=lambda: ["F_WT", "M_WT", "F_KO", "M_KO"],
    )
    interaction_pvalue: float | None = None
    title: str = "CV of instantaneous velocity"


def _demo() -> CVVelocityInput:
    rng = np.random.default_rng(807)
    return CVVelocityInput(
        cv_velocity_by_group={
            "F_WT": rng.gamma(4.5, 0.07, 62).tolist(),   # ≈0.32
            "M_WT": rng.gamma(4.0, 0.08, 58).tolist(),   # ≈0.32
            "F_KO": rng.gamma(6.5, 0.10, 60).tolist(),   # ≈0.65, larger spread
            "M_KO": rng.gamma(4.2, 0.09, 63).tolist(),   # ≈0.38
        },
        interaction_pvalue=2.3e-3,
    )


_META = RecipeMetadata(
    name="sex_stratified_cvvelocity",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.split_violin,
    answers_question=(
        "How does the coefficient of variation of instantaneous velocity "
        "distribute by sex × genotype, and is there a sex×genotype interaction?"
    ),
    required_fields=("cv_velocity_by_group",),
    optional_fields=("sex_x_genotype_order", "interaction_pvalue", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=(
        "process_length_distribution_by_sex",
        "protrusion_length_velocity_joint",
    ),
)


@register_recipe(
    metadata=_META,
    contract=CVVelocityInput,
    demo_contract=_demo,
)
def render(contract: CVVelocityInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette("sex_x_genotype")

    groups = [g for g in contract.sex_x_genotype_order
              if g in contract.cv_velocity_by_group]
    positions = list(range(len(groups)))
    data = [np.asarray(contract.cv_velocity_by_group[g], float) for g in groups]

    parts = ax.violinplot(data, positions=positions, widths=0.78,
                          showmeans=False, showmedians=False, showextrema=False)
    for i, pc in enumerate(parts["bodies"]):
        color = (palette.pick(groups[i]) if groups[i] in palette.semantic
                 else palette[i % len(palette.colors)])
        pc.set_facecolor(color)
        pc.set_edgecolor("#333333")
        pc.set_alpha(0.55)

    rng = np.random.default_rng(809)
    for pos, vals, g in zip(positions, data, groups):
        color = (palette.pick(g) if g in palette.semantic else palette[0])
        jitter = rng.uniform(-0.13, 0.13, vals.size)
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

    # Sex × genotype highlight: interaction bracket spanning the KO pair.
    if contract.interaction_pvalue is not None and len(groups) >= 4:
        y_top = float(max(v.max() for v in data)) * 1.08
        ax.plot([0, 0, 3, 3], [y_top - 0.01, y_top, y_top, y_top - 0.01],
                color="#111111", lw=0.8, zorder=5)
        stars = ("***" if contract.interaction_pvalue < 1e-3
                 else "**" if contract.interaction_pvalue < 1e-2
                 else "*" if contract.interaction_pvalue < 5e-2 else "ns")
        ax.text(1.5, y_top + 0.01,
                f"sex × genotype  {stars}  p = {smart_fmt(contract.interaction_pvalue)}",
                ha="center", va="bottom", fontsize=7.0, color="#111111")

    if len(groups) == 4:
        ax.axvline(1.5, color="#CCCCCC", lw=0.5, ls=":", zorder=0)

    ax.set_xticks(positions)
    ax.set_xticklabels(groups, fontsize=7.0)
    ax.set_ylabel(r"CV of instantaneous velocity")
    ax.set_title(contract.title, fontsize=9.0, pad=8)
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
