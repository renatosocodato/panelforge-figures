"""emmeans contrast grid — pairwise contrasts between groups with CIs + p-values."""

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


class ContrastRow(RecipeContract):
    name: str
    estimate: float
    ci_lo: float
    ci_hi: float
    p: float


class EmmeansContrastInput(RecipeContract):
    contrasts: list[ContrastRow] = Field(..., min_length=2)
    alpha: float = 0.05
    x_label: str = "contrast (95% CI)"
    title: str = "Estimated marginal contrasts"


def _demo() -> EmmeansContrastInput:
    rows = [
        ContrastRow(name="F_WT − M_WT", estimate=0.25, ci_lo=0.05, ci_hi=0.45, p=0.012),
        ContrastRow(name="F_KO − M_KO", estimate=-0.15, ci_lo=-0.35, ci_hi=0.05, p=0.130),
        ContrastRow(name="F_WT − F_KO", estimate=0.52, ci_lo=0.28, ci_hi=0.76, p=0.0008),
        ContrastRow(name="M_WT − M_KO", estimate=0.12, ci_lo=-0.05, ci_hi=0.29, p=0.16),
        ContrastRow(name="WT − KO (pooled)", estimate=0.32, ci_lo=0.18, ci_hi=0.46, p=0.00005),
        ContrastRow(name="F − M (pooled)", estimate=0.05, ci_lo=-0.10, ci_hi=0.20, p=0.51),
    ]
    return EmmeansContrastInput(contrasts=rows)


_META = RecipeMetadata(
    name="emmeans_contrast_grid",
    modality="mixed_effects_models",
    family=RecipeFamily.coef_forest,
    answers_question="Which pairwise contrasts (adjusted marginal means) are significant, and by how much?",
    required_fields=("contrasts",),
    optional_fields=("alpha", "x_label", "title"),
    file_format_hints=("csv", "rds"),
    alternatives_in_modality=("sex_x_genotype_interaction_forest", "marginal_effects_ribbon"),
)


@register_recipe(metadata=_META, contract=EmmeansContrastInput, demo_contract=_demo)
def render(contract: EmmeansContrastInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    sig_color = "#1B5E20"
    nonsig_color = "#888888"

    rows = list(contract.contrasts)
    y = np.arange(len(rows))[::-1]

    # Zero reference.
    ax.axvline(0, color="#888888", lw=0.7, ls="--", zorder=1)

    for yi, r in zip(y, rows):
        sig = r.p < contract.alpha
        color = sig_color if sig else nonsig_color
        ax.plot([r.ci_lo, r.ci_hi], [yi, yi],
                color=color, lw=1.1, zorder=2)
        for x_end in (r.ci_lo, r.ci_hi):
            ax.plot([x_end, x_end], [yi - 0.17, yi + 0.17],
                    color=color, lw=1.1, zorder=2)
        ax.scatter([r.estimate], [yi], s=28, color=color,
                   edgecolor="white", linewidth=0.9, zorder=3)

    # x-limits with room for right-side value + p-value labels.
    xlo = min(r.ci_lo for r in rows)
    xhi = max(r.ci_hi for r in rows)
    span = max(xhi - xlo, 0.2)
    ax.set_xlim(xlo - 0.05 * span, xhi + 0.35 * span)
    x_text = xhi + 0.04 * span

    for yi, r in zip(y, rows):
        sig = r.p < contract.alpha
        color = sig_color if sig else nonsig_color
        ax.text(x_text, yi,
                f"{smart_fmt(r.estimate)}   p={smart_fmt(r.p)}",
                va="center", ha="left",
                fontsize=6.8, color=color)

    ax.set_yticks(y)
    ax.set_yticklabels([r.name for r in rows], fontsize=7.2)
    ax.set_xlabel(contract.x_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    # Legend pill.
    ax.text(0.01, 0.99,
            f"significance at α = {smart_fmt(contract.alpha)}",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.4, color="#444444",
            bbox=dict(boxstyle="round,pad=0.20", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=5)
    _ = palette
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
