"""GGE branch-selectivity permutation bar — observed fraction of
GGE-enriched vs non-GGE pathways with male-biased phospho score,
with permutation null distribution overlaid as faint grey jitter
behind the observed bars; per-bar empirical p-value annotation.

Coef-forest family: >=3 markers + >=1 reference line.
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
from ._shared import GGEBranchRow, PermutationNullBundle


class GGEBranchPermutationInput(RecipeContract):
    branches: list[GGEBranchRow] = Field(..., min_length=3)
    null: PermutationNullBundle = Field(...)
    chance_level: float = 0.50
    title: str = "GGE branch-selectivity permutation bar"


def _demo() -> GGEBranchPermutationInput:
    rng = np.random.default_rng(815)
    # Per the manuscript: GGE 60.5% Male>Female phospho vs non-GGE
    # 30.1% (perm p<0.001).
    branches = [
        GGEBranchRow(branch="GGE-enriched", observed=0.605,
                     n_pathways=43, is_gge=True),
        GGEBranchRow(branch="non-GGE", observed=0.301,
                     n_pathways=387, is_gge=False),
        GGEBranchRow(branch="random subsample", observed=0.498,
                     n_pathways=43, is_gge=False),
    ]
    null = PermutationNullBundle(
        label="GGE branch selectivity",
        null_values=rng.normal(0.50, 0.05, 200).tolist(),
        p_perm=0.0010,
    )
    return GGEBranchPermutationInput(branches=branches, null=null)


_META = RecipeMetadata(
    name="gge_branch_selectivity_permutation_bar",
    modality="omics_differential",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "Across pathway branches, what fraction of GGE-enriched "
        "vs non-GGE pathways show male-biased phospho scores, and "
        "is the GGE-vs-non-GGE difference larger than the "
        "permutation-shuffle null?"
    ),
    required_fields=("branches", "null"),
    optional_fields=("chance_level", "title"),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("ora_dotplot_by_ontology",),
)


@register_recipe(
    metadata=_META,
    contract=GGEBranchPermutationInput,
    demo_contract=_demo,
)
def render(contract: GGEBranchPermutationInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.0, 3.8))
    AESTHETIC.apply_to_ax(ax)

    branches = list(contract.branches)
    n = len(branches)
    y = np.arange(n)
    chance = contract.chance_level

    # Reference line at chance level.
    ax.axvline(chance, color="#888888", lw=0.7, ls="--", zorder=2,
               label=f"chance = {smart_fmt(chance)}")

    # Permutation-null jitter — drawn behind observed bars.
    null_arr = np.asarray(contract.null.null_values, float)
    rng = np.random.default_rng(816)
    for yi in y:
        y_jitter = yi + rng.uniform(-0.18, 0.18, null_arr.size)
        ax.scatter(null_arr, y_jitter,
                   s=8, color="#BDBDBD", alpha=0.25,
                   edgecolor="none", zorder=3)

    # Observed bars (the >=3 markers for the family rule).
    for yi, b in zip(y, branches):
        colour = "#26A69A" if b.is_gge else "#9E9E9E"
        ax.plot([chance, b.observed], [yi, yi],
                color=colour, lw=2.2, alpha=0.85, zorder=4)
        ax.scatter([b.observed], [yi], s=66, marker="o",
                   facecolor=colour, edgecolor="white",
                   linewidth=0.6, zorder=6)
        # Inline observed-fraction + n callout.
        ax.text(b.observed + 0.02, yi,
                f"{smart_fmt(b.observed * 100)}%  ·  n={b.n_pathways}",
                ha="left", va="center", fontsize=6.4,
                color=colour, fontweight="bold", zorder=7)

    ax.set_yticks(y)
    ax.set_yticklabels([b.branch for b in branches], fontsize=6.8)
    ax.invert_yaxis()
    ax.set_xlabel("fraction Male > Female phospho")
    ax.set_xlim(0.0, 1.0)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor="#26A69A", markeredgecolor="white",
               markersize=6, label="GGE-enriched"),
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor="#9E9E9E", markeredgecolor="white",
               markersize=6, label="non-GGE / random"),
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor="#BDBDBD", markeredgecolor="none",
               markersize=4, label="permutation null"),
        Line2D([0], [0], color="#888888", ls="--", lw=0.7,
               label=f"chance = {smart_fmt(chance)}"),
    ]
    ax.legend(handles=handles, fontsize=6.4, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.16),
              ncols=4, handlelength=1.0)

    ax.set_title(
        f"{contract.title}  ·  permutation p = "
        f"{smart_fmt(contract.null.p_perm)}  "
        f"(n_perms = {len(null_arr)})",
        fontsize=8.2, pad=4,
    )
    return ax
