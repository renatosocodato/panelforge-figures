"""Group-level emmeans with pairwise significance brackets.

Distinct from `emmeans_contrast_grid` (which plots Δ between groups
as a forest of contrasts): this panel plots the *absolute* estimated
marginal mean per group on the response scale, with pairwise brackets
and stars marking significant comparisons (Bonferroni by default).
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


class PairwiseContrast(RecipeContract):
    group_a: str
    group_b: str
    p_adj: float


class EmmeansWithPairwiseInput(RecipeContract):
    groups: list[str] = Field(..., min_length=2)
    emmeans: list[float] = Field(...)
    ci_lo: list[float] = Field(...)
    ci_hi: list[float] = Field(...)
    pairwise: list[PairwiseContrast] = Field(default_factory=list)
    alpha: float = 0.05
    outcome_label: str = "estimated marginal mean"
    title: str = "emmeans per group (response scale)"


def _demo() -> EmmeansWithPairwiseInput:
    groups = ["F_WT", "M_WT", "F_KO", "M_KO"]
    emm = [1.25, 1.18, 0.45, 1.05]
    se = [0.08, 0.09, 0.10, 0.08]
    lo = [e - 1.96 * s for e, s in zip(emm, se)]
    hi = [e + 1.96 * s for e, s in zip(emm, se)]
    pw = [
        PairwiseContrast(group_a="F_WT", group_b="F_KO", p_adj=0.00005),
        PairwiseContrast(group_a="M_WT", group_b="F_KO", p_adj=0.00042),
        PairwiseContrast(group_a="F_KO", group_b="M_KO", p_adj=0.00128),
        PairwiseContrast(group_a="F_WT", group_b="M_WT", p_adj=0.62),
        PairwiseContrast(group_a="F_WT", group_b="M_KO", p_adj=0.24),
        PairwiseContrast(group_a="M_WT", group_b="M_KO", p_adj=0.38),
    ]
    return EmmeansWithPairwiseInput(
        groups=groups, emmeans=emm, ci_lo=lo, ci_hi=hi, pairwise=pw,
    )


def _stars(p: float) -> str:
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "ns"


_META = RecipeMetadata(
    name="group_level_emmeans_with_pairwise",
    modality="mixed_effects_models",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "What are the estimated marginal means per condition (response "
        "scale), with pairwise-significance brackets above the groups?"
    ),
    required_fields=("groups", "emmeans", "ci_lo", "ci_hi"),
    optional_fields=("pairwise", "alpha", "outcome_label", "title"),
    file_format_hints=("csv", "rds"),
    alternatives_in_modality=(
        "emmeans_contrast_grid",
        "sex_x_genotype_interaction_forest",
    ),
)


@register_recipe(
    metadata=_META,
    contract=EmmeansWithPairwiseInput,
    demo_contract=_demo,
)
def render(contract: EmmeansWithPairwiseInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.8))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    groups = contract.groups
    emm = np.asarray(contract.emmeans, float)
    lo = np.asarray(contract.ci_lo, float)
    hi = np.asarray(contract.ci_hi, float)
    x = np.arange(len(groups))

    # Vertical CI bars + markers per group.
    for i, g in enumerate(groups):
        color = (palette.pick(g) if g in palette.semantic
                 else palette[i % len(palette.colors)])
        ax.plot([x[i], x[i]], [lo[i], hi[i]], color=color, lw=1.3, zorder=3)
        # Caps.
        for y_end in (lo[i], hi[i]):
            ax.plot([x[i] - 0.10, x[i] + 0.10], [y_end, y_end],
                    color=color, lw=1.3, zorder=3)
        ax.scatter([x[i]], [emm[i]], s=42, color=color,
                   edgecolor="white", linewidth=0.9, zorder=4)
        # Emmean label below marker.
        ax.text(x[i], lo[i], smart_fmt(emm[i]),
                ha="center", va="top", fontsize=6.6, color=color,
                zorder=5)

    # Significance brackets stacked above the tallest CI.
    y_top = float(hi.max())
    span = float(hi.max() - lo.min())
    bracket_base = y_top + 0.08 * span
    bracket_step = 0.075 * span
    sig_pairs = [pc for pc in contract.pairwise if pc.p_adj < contract.alpha]
    # Order brackets bottom-up by gap between groups so shorter arcs go first.
    gi = {g: i for i, g in enumerate(groups)}
    sig_pairs.sort(key=lambda pc: abs(gi[pc.group_a] - gi[pc.group_b]))
    for k, pc in enumerate(sig_pairs):
        xa, xb = gi[pc.group_a], gi[pc.group_b]
        y_b = bracket_base + k * bracket_step
        ax.plot([xa, xa, xb, xb],
                [y_b - 0.012 * span, y_b, y_b, y_b - 0.012 * span],
                color="#333333", lw=0.8, zorder=6)
        ax.text((xa + xb) / 2, y_b + 0.005 * span,
                _stars(pc.p_adj),
                ha="center", va="bottom", fontsize=7.6,
                fontweight="bold", color="#111111", zorder=7)

    # Optional ns brackets as grey, single (only for adjacent pairs) — keep figure uncluttered.
    ns_adjacent = [pc for pc in contract.pairwise
                   if pc.p_adj >= contract.alpha
                   and abs(gi[pc.group_a] - gi[pc.group_b]) == 1]
    for pc in ns_adjacent:
        xa, xb = gi[pc.group_a], gi[pc.group_b]
        y_b = bracket_base - 0.05 * span
        ax.plot([xa, xa, xb, xb],
                [y_b - 0.012 * span, y_b, y_b, y_b - 0.012 * span],
                color="#AAAAAA", lw=0.6, zorder=5)
        ax.text((xa + xb) / 2, y_b + 0.005 * span, "ns",
                ha="center", va="bottom", fontsize=6.2, color="#888888",
                zorder=5)

    ax.set_xticks(x)
    ax.set_xticklabels(groups, fontsize=7.4)
    ax.set_ylabel(contract.outcome_label)
    ax.set_ylim(
        lo.min() - 0.06 * span,
        bracket_base + max(len(sig_pairs), 1) * bracket_step + 0.04 * span,
    )
    ax.set_title(f"{contract.title}  ·  α = {smart_fmt(contract.alpha)} (adj.)",
                 fontsize=9.0, pad=4)
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
