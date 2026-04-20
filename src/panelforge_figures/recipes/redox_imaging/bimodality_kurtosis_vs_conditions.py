"""Condition-level bimodality statistics — BC, kurtosis, Hartigan's dip.

Per condition, plots three complementary bimodality scalars as grouped
horizontal bars:
  - Bimodality Coefficient BC (threshold 5/9 ≈ 0.555)
  - Excess kurtosis (negative excess → flatter → more bimodal)
  - Hartigan's dip statistic

A filled bar crosses the significance reference for each statistic;
a star marks conditions where all three agree.

Distinct from `bimodality_coefficient_grid` which plots a single BC
statistic over condition × time.
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


class BimodalityStatsInput(RecipeContract):
    condition_names: list[str] = Field(..., min_length=2)
    bimodality_coef: list[float] = Field(
        ..., description="Pearson's BC (bimodal if > 5/9)"
    )
    excess_kurtosis: list[float] = Field(
        ..., description="excess kurtosis (bimodal if < 0)"
    )
    dip_statistic: list[float] = Field(
        ..., description="Hartigan's dip statistic (bimodal if > ≈ 0.03)"
    )
    title: str = "Bimodality statistics per condition"


def _demo() -> BimodalityStatsInput:
    conditions = ["baseline", "LPS 100ng", "LPS + NAC", "H2O2 50μM", "IFN-γ"]
    bc = [0.39, 0.64, 0.48, 0.72, 0.58]
    kurt = [0.45, -0.22, 0.18, -0.48, -0.12]
    dip = [0.012, 0.045, 0.018, 0.062, 0.039]
    return BimodalityStatsInput(
        condition_names=conditions,
        bimodality_coef=bc,
        excess_kurtosis=kurt,
        dip_statistic=dip,
    )


_META = RecipeMetadata(
    name="bimodality_kurtosis_vs_conditions",
    modality="redox_imaging",
    family=RecipeFamily.ladder,
    answers_question=(
        "Across conditions, how do single-cell bimodality statistics "
        "(BC, kurtosis, Hartigan's dip) compare?"
    ),
    required_fields=(
        "condition_names", "bimodality_coef", "excess_kurtosis",
        "dip_statistic",
    ),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("bimodality_coefficient_grid",),
)


@register_recipe(
    metadata=_META,
    contract=BimodalityStatsInput,
    demo_contract=_demo,
)
def render(contract: BimodalityStatsInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.0, 3.6))
    AESTHETIC.apply_to_ax(ax)

    conditions = contract.condition_names
    n = len(conditions)
    bc = np.asarray(contract.bimodality_coef, float)
    kurt = np.asarray(contract.excess_kurtosis, float)
    dip = np.asarray(contract.dip_statistic, float)

    y = np.arange(n)[::-1]
    row_h = 0.22

    # Thresholds for each statistic.
    bc_thr = 5 / 9
    kurt_thr = 0.0
    dip_thr = 0.03

    # Per-statistic bar group.
    # BC on row y+row_h, kurt on row y, dip on row y-row_h.
    #
    # BC: bar length = bc. Bar filled if BC > threshold, else outline.
    bc_color = "#1565C0"
    kurt_color = "#8E24AA"
    dip_color = "#2E7D32"

    # Normalise each stat to 0-1 for shared visual length.
    def scaled(x, thr, limit):
        return np.clip(x / limit, 0, 1), thr / limit

    bc_scaled, bc_t = scaled(bc, bc_thr, 1.0)
    # kurt centered at 0 → shift so +0.8 → 1, -0.8 → 0; threshold at 0 → 0.5
    kurt_scaled = np.clip((kurt + 0.8) / 1.6, 0, 1)
    kurt_t = 0.5
    dip_scaled, dip_t = scaled(dip, dip_thr, 0.08)

    for yi, i in zip(y, range(n)):
        for off, val, thr_v, col, passed in [
            (row_h, bc_scaled[i], bc_t, bc_color, bc[i] > bc_thr),
            (0.0, kurt_scaled[i], kurt_t, kurt_color, kurt[i] < kurt_thr),
            (-row_h, dip_scaled[i], dip_t, dip_color, dip[i] > dip_thr),
        ]:
            ax.barh(yi + off, val, height=row_h * 0.9,
                    color=col if passed else "white",
                    edgecolor=col, linewidth=1.0,
                    alpha=0.85 if passed else 1.0, zorder=3)
            # Threshold tick.
            ax.plot([thr_v, thr_v],
                    [yi + off - row_h * 0.45, yi + off + row_h * 0.45],
                    color="#111111", lw=0.6, zorder=4)

        # Star marker if all three statistics agree (bimodal). Uses a
        # matplotlib scatter marker so it renders in Helvetica-safe fonts.
        if bc[i] > bc_thr and kurt[i] < kurt_thr and dip[i] > dip_thr:
            ax.scatter([1.04], [yi], s=70, marker="*",
                       color="#C62828", edgecolor="white",
                       linewidth=0.6, zorder=6,
                       transform=ax.get_yaxis_transform(), clip_on=False)
        # Numeric labels on the right of each bar.
        ax.text(bc_scaled[i] + 0.01, yi + row_h,
                f"BC={smart_fmt(bc[i])}",
                va="center", ha="left", fontsize=6.2, color=bc_color,
                zorder=5)
        ax.text(kurt_scaled[i] + 0.01, yi,
                f"κ={smart_fmt(kurt[i])}",
                va="center", ha="left", fontsize=6.2, color=kurt_color,
                zorder=5)
        ax.text(dip_scaled[i] + 0.01, yi - row_h,
                f"dip={smart_fmt(dip[i])}",
                va="center", ha="left", fontsize=6.2, color=dip_color,
                zorder=5)

    ax.set_xlim(0, 1.22)
    ax.set_ylim(-0.8, n - 0.2)
    ax.set_yticks(y)
    ax.set_yticklabels(conditions, fontsize=7.2)
    ax.set_xticks([])
    ax.set_xlabel("scaled statistic  (tick = threshold;  * = all three agree)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    # Legend for the three statistics.
    from matplotlib.patches import Patch
    proxies = [
        Patch(facecolor=bc_color, edgecolor=bc_color, label="BC (>5/9)"),
        Patch(facecolor=kurt_color, edgecolor=kurt_color, label="κ (<0)"),
        Patch(facecolor=dip_color, edgecolor=dip_color, label="dip (>0.03)"),
    ]
    ax.legend(handles=proxies, fontsize=6.6, frameon=False,
              loc="lower right", ncols=3, handlelength=1.3,
              bbox_to_anchor=(1.0, -0.20))
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
