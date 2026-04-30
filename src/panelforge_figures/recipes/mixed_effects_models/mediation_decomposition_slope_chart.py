"""Mediation decomposition slope chart — direct vs indirect effect
estimates per stratum, drawn as paired markers connected by slope
lines (direct = solid, indirect = dashed).

Each row is one stratum (sex × genotype cell, or pre/post intervention
cell); the recipe shows the partition of the total effect into a
direct + indirect (mediated) component, with 95% CI whiskers and an
optional proportion-mediated annotation in the right margin.

Scatter-collapse family: >=1 scatter + >=1 fit line. Satisfied by the
direct + indirect markers per stratum + the per-row connecting slope
line + the zero-effect reference line.
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
from ._shared import MediationPath


class MediationSlopeInput(RecipeContract):
    paths: list[MediationPath] = Field(..., min_length=2)
    title: str = "Mediation decomposition (direct + indirect)"


def _demo() -> MediationSlopeInput:
    rng = np.random.default_rng(822)
    rows = [
        ("female · CTL",  0.62, 0.18),
        ("female · CKO",  0.41, 0.27),
        ("male · CTL",    0.34, 0.42),
        ("male · CKO",    0.18, 0.55),
    ]
    paths = []
    for stratum, direct, indirect in rows:
        d_w = 0.10 + rng.uniform(0.02, 0.04)
        i_w = 0.10 + rng.uniform(0.02, 0.04)
        prop = indirect / max(abs(direct + indirect), 1e-6)
        paths.append(MediationPath(
            stratum=stratum,
            direct_effect=direct,
            direct_ci_lo=direct - d_w,
            direct_ci_hi=direct + d_w,
            indirect_effect=indirect,
            indirect_ci_lo=indirect - i_w,
            indirect_ci_hi=indirect + i_w,
            proportion_mediated=prop,
        ))
    return MediationSlopeInput(paths=paths)


_META = RecipeMetadata(
    name="mediation_decomposition_slope_chart",
    modality="mixed_effects_models",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Per stratum, how is the total treatment effect partitioned "
        "into a direct and an indirect (mediated) component, and how "
        "stable is that partition across strata?"
    ),
    required_fields=("paths",),
    optional_fields=("title",),
    file_format_hints=("csv", "yaml"),
    alternatives_in_modality=("posterior_contrast_density",),
)


@register_recipe(
    metadata=_META,
    contract=MediationSlopeInput,
    demo_contract=_demo,
)
def render(contract: MediationSlopeInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.4))
    AESTHETIC.apply_to_ax(ax)

    paths = list(contract.paths)
    n = len(paths)
    y = np.arange(n)[::-1]

    # Reference: zero-effect vertical line.
    ax.axvline(0.0, color="#888888", lw=0.7, ls="--", zorder=1,
               label="zero effect")

    direct_color = "#37474F"
    indirect_color = "#FFB300"

    for yi, p in zip(y, paths):
        # Per-row connecting slope line (the fit line for the
        # scatter_collapse family rule).
        ax.plot([p.direct_effect, p.indirect_effect], [yi, yi],
                color="#BDBDBD", lw=0.8, zorder=2)
        # Direct effect: marker + CI whisker (solid).
        ax.plot([p.direct_ci_lo, p.direct_ci_hi], [yi, yi],
                color=direct_color, lw=1.0, zorder=3)
        ax.scatter([p.direct_effect], [yi], s=44, marker="o",
                   facecolor=direct_color, edgecolor="white",
                   linewidth=0.7, zorder=5)
        # Indirect effect: marker + CI whisker (dashed line for visual
        # distinction).
        ax.plot([p.indirect_ci_lo, p.indirect_ci_hi], [yi, yi],
                color=indirect_color, lw=1.0, ls="--", zorder=3)
        ax.scatter([p.indirect_effect], [yi], s=44, marker="s",
                   facecolor=indirect_color, edgecolor="white",
                   linewidth=0.7, zorder=5)

    # Right-margin proportion-mediated annotation.
    all_x = []
    for p in paths:
        all_x += [p.direct_ci_lo, p.direct_ci_hi,
                  p.indirect_ci_lo, p.indirect_ci_hi]
    span = max(max(all_x) - min(all_x), 0.10)
    ax.set_xlim(min(all_x) - 0.05 * span, max(all_x) + 0.30 * span)
    xhi = ax.get_xlim()[1]
    gap = 0.012 * (xhi - ax.get_xlim()[0])
    for yi, p in zip(y, paths):
        right_x = max(p.direct_ci_hi, p.indirect_ci_hi)
        if p.proportion_mediated is not None:
            ax.text(right_x + gap, yi,
                    f"prop. mediated = {smart_fmt(p.proportion_mediated)}",
                    ha="left", va="center", fontsize=6.4,
                    color="#222222", zorder=6)

    ax.set_yticks(y)
    ax.set_yticklabels([p.stratum for p in paths], fontsize=7.0)
    ax.set_xlabel("effect size (95% CI)")
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], marker="o", color=direct_color, lw=1.0,
               markerfacecolor=direct_color, markeredgecolor="white",
               markersize=6, label="direct effect"),
        Line2D([0], [0], marker="s", color=indirect_color, lw=1.0,
               ls="--", markerfacecolor=indirect_color,
               markeredgecolor="white", markersize=6,
               label="indirect (mediated)"),
        Line2D([0], [0], color="#888888", ls="--", lw=0.7,
               label="zero effect"),
    ]
    ax.legend(handles=handles, fontsize=6.4, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.14),
              ncols=3, handlelength=1.6)

    ax.set_title(contract.title, fontsize=8.2, pad=4)
    return ax
