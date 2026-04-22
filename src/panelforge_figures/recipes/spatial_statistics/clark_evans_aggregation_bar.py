"""Clark-Evans aggregation-index ladder — per-condition CE ± CI with
CSR reference at 1.0. Distinct from `ripley_l_function` (scale-
dependent): this is a single summary statistic per condition.
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


class ClarkEvansInput(RecipeContract):
    condition_names: list[str] = Field(..., min_length=3)
    ce_index: list[float] = Field(..., description="Clark-Evans index per condition")
    ce_lo: list[float] = Field(..., description="CI lower bound")
    ce_hi: list[float] = Field(..., description="CI upper bound")
    n_points: list[int] | None = None
    title: str = "Clark-Evans aggregation index"


def _demo() -> ClarkEvansInput:
    rng = np.random.default_rng(1031)
    names = ["control", "LPS", "IFNγ", "TNFα", "IL-4"]
    true_ce = [0.98, 0.62, 0.71, 0.55, 1.18]
    ce = [float(c + rng.normal(0, 0.02)) for c in true_ce]
    se = rng.uniform(0.04, 0.08, len(names))
    return ClarkEvansInput(
        condition_names=names,
        ce_index=ce,
        ce_lo=(np.array(ce) - 1.96 * se).tolist(),
        ce_hi=(np.array(ce) + 1.96 * se).tolist(),
        n_points=[400, 380, 410, 395, 420],
    )


_META = RecipeMetadata(
    name="clark_evans_aggregation_bar",
    modality="spatial_statistics",
    family=RecipeFamily.ladder,
    answers_question=(
        "Across conditions, is the point pattern clustered (CE < 1), "
        "random (CE ≈ 1), or dispersed (CE > 1)?"
    ),
    required_fields=("condition_names", "ce_index", "ce_lo", "ce_hi"),
    optional_fields=("n_points", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("ripley_l_function",),
)


@register_recipe(
    metadata=_META,
    contract=ClarkEvansInput,
    demo_contract=_demo,
)
def render(contract: ClarkEvansInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.4))
    AESTHETIC.apply_to_ax(ax)

    names = contract.condition_names
    ce = np.asarray(contract.ce_index, float)
    lo = np.asarray(contract.ce_lo, float)
    hi = np.asarray(contract.ce_hi, float)

    # Sort by CE.
    order = np.argsort(ce)
    names_s = [names[i] for i in order]
    ce_s = ce[order]
    lo_s = lo[order]
    hi_s = hi[order]

    y = np.arange(len(names_s))

    # CSR reference band.
    ax.axvspan(0.95, 1.05, color="#DDDDDD", alpha=0.5, zorder=1,
               label="CSR (CE ≈ 1)")
    ax.axvline(1.0, color="#888888", lw=0.8, ls="--", zorder=2)

    # Bars from CSR reference (1.0) to CE.
    for i, (c, lo_i, hi_i) in enumerate(zip(ce_s, lo_s, hi_s)):
        # Bar color by interpretation.
        if c < 0.95:
            color = "#C62828"  # clustered
        elif c > 1.05:
            color = "#2E7D32"  # dispersed
        else:
            color = "#888888"  # random
        width = c - 1.0
        ax.barh(i, width, left=1.0,
                color=color, edgecolor="white", linewidth=0.7,
                alpha=0.85, zorder=3, height=0.7)
        # CI whiskers.
        ax.plot([lo_i, hi_i], [i, i], color="#333333", lw=1.0, zorder=4)

    # Per-bar numeric label.
    for i, c in enumerate(ce_s):
        label_x = c + (0.02 if c >= 1.0 else -0.02)
        ha = "left" if c >= 1.0 else "right"
        ax.text(label_x, i, smart_fmt(float(c)),
                ha=ha, va="center", fontsize=6.8, color="#333333",
                zorder=5)

    ax.set_yticks(y)
    ax.set_yticklabels(names_s, fontsize=7.0)
    ax.set_xlabel("Clark-Evans index (R_obs / R_CSR)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="lower right",
              handlelength=1.2)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Footer: interpretation counts.
    n_clust = int((ce_s < 0.95).sum())
    n_rand = int(((ce_s >= 0.95) & (ce_s <= 1.05)).sum())
    n_disp = int((ce_s > 1.05).sum())
    ax.text(0.02, 0.97,
            f"clustered: {n_clust}  random: {n_rand}  dispersed: {n_disp}",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.4, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)

    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    return ax
