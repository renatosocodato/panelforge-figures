"""Quartile stacked bar by factor — composition stacked bar showing
% occupancy per quartile across conditions (sex × genotype factorial).

Each condition is one horizontal bar of stacked Rectangles, one per
quartile (Q1 lowest → Q4 highest), coloured on a 4-tier viridis ramp.
Per-cell-quartile fraction annotations sit centred in each Rectangle
when the segment is wide enough; per-condition `n` annotations sit
on the right margin.

Matrix family: >=4 cell patches OR >=1 imshow. Satisfied by
4 conditions × 4 quartiles = 16 Rectangle patches.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    StatisticalContract,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC
from ._shared import QuartileOccupancyBin


class QuartileStackedBarInput(RecipeContract):
    bins: list[QuartileOccupancyBin] = Field(..., min_length=4)
    quartile_label: str = "dissipation quartile"
    title: str = "Quartile occupancy by sex × genotype"


def _demo() -> QuartileStackedBarInput:
    rng = np.random.default_rng(830)
    # Manuscript F5D values: F-CTL Q4 = 0.40 (top dissipation surplus);
    # M-CKO Q1 = 0.45 (low surveillance regime).
    cond_fractions = {
        "female · CTL": [0.18, 0.20, 0.22, 0.40],
        "female · CKO": [0.30, 0.28, 0.22, 0.20],
        "male · CTL":   [0.22, 0.28, 0.28, 0.22],
        "male · CKO":   [0.45, 0.28, 0.16, 0.11],
    }
    bins: list[QuartileOccupancyBin] = []
    for cond, fracs in cond_fractions.items():
        n_total = int(rng.integers(28, 38))
        for q, f in enumerate(fracs, start=1):
            bins.append(QuartileOccupancyBin(
                condition=cond, quartile=q, fraction=f,
                n_cells=int(round(f * n_total)),
            ))
    return QuartileStackedBarInput(bins=bins)


_META = RecipeMetadata(
    name="quartile_stacked_bar_by_factor",
    modality="biophysics_scaling",
    family=RecipeFamily.matrix,
    answers_question=(
        "Across sex × genotype conditions, what fraction of cells "
        "occupies each dissipation / energetic quartile, and where "
        "are the top/bottom-quartile shifts strongest?"
    ),
    required_fields=("bins",),
    optional_fields=("quartile_label", "title"),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("confinement_ratio_distribution_by_genotype",),
    statistical_contract=StatisticalContract(
        min_n_per_group=20,
        distribution_assumption="unit_interval",
        independence="iid",
        rendered_claim_template="fraction = {frac:.2%}",
        refuses_when=("underpowered", "unit_interval_violation"),
    ),
)


@register_recipe(
    metadata=_META,
    contract=QuartileStackedBarInput,
    demo_contract=_demo,
)
def render(contract: QuartileStackedBarInput, ax=None, **_):
    import matplotlib.patches as mpatches
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 3.4))
    AESTHETIC.apply_to_ax(ax)

    # Group bins by condition (preserve insertion order via dict).
    conds: dict[str, dict[int, QuartileOccupancyBin]] = {}
    for b in contract.bins:
        conds.setdefault(b.condition, {})[b.quartile] = b

    cond_names = list(conds.keys())
    n_conds = len(cond_names)
    quartiles = sorted({b.quartile for b in contract.bins})
    # 4-tier viridis sample (ascending quartile = darker → lighter green).
    import matplotlib as mpl
    cmap = mpl.colormaps["viridis"].resampled(len(quartiles))
    quart_colours = [cmap(i) for i in range(len(quartiles))]

    for yi, cond in enumerate(cond_names):
        x_left = 0.0
        n_total = sum(
            (conds[cond][q].n_cells or 0) for q in quartiles
        )
        for qi, q in enumerate(quartiles):
            b = conds[cond].get(q)
            if b is None:
                continue
            colour = quart_colours[qi]
            ax.add_patch(mpatches.Rectangle(
                (x_left, yi - 0.40),
                b.fraction, 0.80,
                facecolor=colour, edgecolor="white",
                linewidth=0.5, alpha=0.92, zorder=3,
            ))
            # Inline percent annotation if segment is wide enough.
            if b.fraction >= 0.13:
                ax.text(x_left + b.fraction / 2, yi,
                        f"{int(round(b.fraction * 100))}%",
                        ha="center", va="center", fontsize=6.4,
                        color="white", fontweight="bold", zorder=5)
            x_left += b.fraction
        # Right-margin n callout.
        if n_total > 0:
            ax.text(1.02, yi, f"n={n_total}",
                    ha="left", va="center", fontsize=6.4,
                    color="#222222", zorder=5)

    ax.set_yticks(range(n_conds))
    ax.set_yticklabels(cond_names, fontsize=7.0)
    ax.set_ylim(n_conds - 0.55, -0.55)   # invert + explicit margins
    ax.set_xlim(-0.01, 1.16)
    ax.set_xlabel("fraction of cells")
    ax.set_xticks(np.linspace(0, 1, 6))
    ax.set_xticklabels([f"{int(t*100)}%" for t in np.linspace(0, 1, 6)],
                       fontsize=6.6)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Legend: per-quartile colour swatches.
    handles = [
        mpatches.Patch(facecolor=quart_colours[i],
                       edgecolor="white", linewidth=0.5,
                       label=f"Q{q} ({contract.quartile_label})")
        for i, q in enumerate(quartiles)
    ]
    ax.legend(handles=handles, fontsize=6.4, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.18),
              ncols=len(quartiles), handlelength=1.0)

    # Title summary: which condition has the strongest Q4 shift?
    q_max = max(quartiles)
    cond_q_max = sorted(
        cond_names,
        key=lambda c: -(conds[c][q_max].fraction if q_max in conds[c] else 0.0),
    )[0]
    cond_q_max_frac = conds[cond_q_max][q_max].fraction
    ax.set_title(
        f"{contract.title}  ·  top-Q{q_max}: {cond_q_max} "
        f"({smart_fmt(cond_q_max_frac * 100)}%)",
        fontsize=8.2, pad=10,
    )
    return ax
