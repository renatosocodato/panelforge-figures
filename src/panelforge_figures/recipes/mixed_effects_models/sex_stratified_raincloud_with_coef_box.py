"""Sex-stratified raincloud + in-panel mixed-model coefficient box.

Answers the reviewer's standing request: "show me the raw data under the
forest". Plots a half-violin + box + jittered rain per sex × genotype,
with a small callout in the upper-right containing the fixed-effect
estimate, 95 % CI and p-value for the sex × genotype interaction term.
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


class RaincloudCoefInput(RecipeContract):
    values_by_stratum: dict[str, list[float]] = Field(
        ..., description="stratum (e.g. 'F_WT','M_WT','F_KO','M_KO') → per-cell values"
    )
    outcome_label: str = "outcome"
    coef_term: str = "sexF:genotypeKO"
    coef_estimate: float = -0.58
    coef_ci: tuple[float, float] = (-0.81, -0.36)
    coef_p: float = 0.00012
    title: str = "Raw distribution + coefficient"


def _demo() -> RaincloudCoefInput:
    rng = np.random.default_rng(104)
    return RaincloudCoefInput(
        values_by_stratum={
            "F_WT": rng.normal(1.25, 0.35, 42).tolist(),
            "M_WT": rng.normal(1.20, 0.32, 40).tolist(),
            "F_KO": rng.normal(0.45, 0.40, 38).tolist(),
            "M_KO": rng.normal(1.05, 0.34, 41).tolist(),
        },
        outcome_label="Δ cell area (z)",
        coef_term="sexF:genotypeKO",
        coef_estimate=-0.62,
        coef_ci=(-0.85, -0.38),
        coef_p=5.1e-5,
    )


_META = RecipeMetadata(
    name="sex_stratified_raincloud_with_coef_box",
    modality="mixed_effects_models",
    family=RecipeFamily.split_violin,
    answers_question=(
        "What does the raw outcome distribution look like under each "
        "sex × genotype stratum, with the fitted coefficient + CI overlaid?"
    ),
    required_fields=("values_by_stratum",),
    optional_fields=(
        "outcome_label", "coef_term", "coef_estimate",
        "coef_ci", "coef_p", "title",
    ),
    file_format_hints=("csv", "parquet", "rds"),
    alternatives_in_modality=(
        "sex_x_genotype_interaction_forest",
        "emmeans_contrast_grid",
    ),
)


@register_recipe(
    metadata=_META,
    contract=RaincloudCoefInput,
    demo_contract=_demo,
)
def render(contract: RaincloudCoefInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.6))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    strata = list(contract.values_by_stratum.keys())
    positions = np.arange(len(strata))
    rng = np.random.default_rng(19)

    for i, name in enumerate(strata):
        vals = np.asarray(contract.values_by_stratum[name], float)
        if vals.size == 0:
            continue
        color = palette.pick(name) if name in palette.semantic else palette[i % len(palette.colors)]

        # Half-violin on the left side of i.
        parts = ax.violinplot(
            vals, positions=[i], widths=0.85, showmeans=False,
            showmedians=False, showextrema=False,
        )
        for body in parts["bodies"]:
            # Clip to left half.
            m = np.mean(body.get_paths()[0].vertices[:, 0])
            body.get_paths()[0].vertices[:, 0] = np.clip(
                body.get_paths()[0].vertices[:, 0], -np.inf, m
            )
            body.set_facecolor(color)
            body.set_alpha(0.55)
            body.set_edgecolor(color)
            body.set_linewidth(0.7)

        # Box summary inline (5-95% + median) on the right half.
        q05, q25, med, q75, q95 = np.quantile(vals, [0.05, 0.25, 0.50, 0.75, 0.95])
        ax.plot([i + 0.05, i + 0.05], [q05, q95], color="#333333", lw=0.8, zorder=3)
        ax.add_patch(
            __import__("matplotlib").patches.Rectangle(
                (i + 0.02, q25), 0.12, q75 - q25,
                facecolor="white", edgecolor="#333333",
                linewidth=0.8, zorder=3,
            )
        )
        ax.scatter([i + 0.08], [med], s=18, color="#111111",
                   edgecolor="white", linewidth=0.7, zorder=4)

        # Rain — jitter points slightly to the right of the box.
        jitter = rng.uniform(0.18, 0.36, vals.size)
        ax.scatter(i + jitter, vals, s=5.5, color=color,
                   alpha=0.70, edgecolor="white", linewidth=0.2, zorder=2)

        # N below the category.
        ax.text(i, ax.get_ylim()[0], f"n={vals.size}",
                ha="center", va="top", fontsize=6.4, color="#555555",
                transform=ax.get_xaxis_transform())

    ax.set_xticks(positions)
    ax.set_xticklabels(strata, fontsize=7.2)
    ax.set_ylabel(contract.outcome_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Coefficient callout (upper-right inside the axes).
    lo, hi = contract.coef_ci
    p_str = f"p={smart_fmt(contract.coef_p)}"
    callout = (
        f"{contract.coef_term}\n"
        f"β = {smart_fmt(contract.coef_estimate)} "
        f"[{smart_fmt(lo)}, {smart_fmt(hi)}]\n"
        f"{p_str}"
    )
    ax.text(
        0.98, 0.97, callout,
        transform=ax.transAxes, ha="right", va="top",
        fontsize=6.6, color="#111111",
        bbox=dict(boxstyle="round,pad=0.30", fc="white",
                  ec="#888888", lw=0.6, alpha=0.95),
        zorder=6,
    )
    return ax
