"""Per-sample cluster-proportion stacked bars with condition-strip annotation.

Unlike `neighborhood_composition_stacked` (per-condition averages),
this recipe plots one stacked bar per biological sample / replicate,
with a thin condition-group strip below to show which samples belong
to which condition.
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
)
from ._aesthetic import AESTHETIC


class SampleCompositionInput(RecipeContract):
    sample_ids: list[str] = Field(..., min_length=2)
    condition_by_sample: list[str] = Field(..., description="one per sample")
    cluster_names: list[str] = Field(..., min_length=2)
    proportions: list[list[float]] = Field(
        ..., description="n_samples × n_clusters row-normalised fractions"
    )
    title: str = "Cluster proportions by sample"


def _demo() -> SampleCompositionInput:
    rng = np.random.default_rng(617)
    clusters = ["homeostatic", "surveillant", "activated", "DAM", "proliferative"]
    samples: list[str] = []
    conds: list[str] = []
    for i in range(5):
        samples.append(f"ctrl_{i+1:02d}")
        conds.append("control")
    for i in range(5):
        samples.append(f"lps_{i+1:02d}")
        conds.append("LPS")
    for i in range(4):
        samples.append(f"rsc_{i+1:02d}")
        conds.append("rescue")
    profiles = {
        "control": [0.45, 0.20, 0.15, 0.12, 0.08],
        "LPS": [0.22, 0.18, 0.30, 0.22, 0.08],
        "rescue": [0.40, 0.20, 0.22, 0.12, 0.06],
    }
    rows = []
    for c in conds:
        base = np.array(profiles[c])
        noise = rng.dirichlet(np.ones(5) * 20, 1)[0] - 0.2
        v = np.clip(base + 0.08 * noise, 1e-3, None)
        v = v / v.sum()
        rows.append(v.tolist())
    return SampleCompositionInput(
        sample_ids=samples,
        condition_by_sample=conds,
        cluster_names=clusters,
        proportions=rows,
    )


_META = RecipeMetadata(
    name="cluster_proportion_stacked_by_sample",
    modality="single_cell_embeddings",
    family=RecipeFamily.matrix,
    answers_question=(
        "Per sample (not per condition), how do cluster proportions "
        "vary?"
    ),
    required_fields=(
        "sample_ids", "condition_by_sample", "cluster_names", "proportions",
    ),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("neighborhood_composition_stacked",),
)


@register_recipe(
    metadata=_META,
    contract=SampleCompositionInput,
    demo_contract=_demo,
)
def render(contract: SampleCompositionInput, ax=None, **_):
    import matplotlib.patches as mpatches

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.2, 3.6))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    samples = contract.sample_ids
    conds = contract.condition_by_sample
    clusters = contract.cluster_names
    P = np.asarray(contract.proportions, float)
    assert P.shape == (len(samples), len(clusters))

    x = np.arange(len(samples))
    bottoms = np.zeros(len(samples))
    for ci, cl in enumerate(clusters):
        color = (palette.pick(cl) if cl in palette.semantic
                 else palette[ci % len(palette.colors)])
        ax.bar(x, P[:, ci], bottom=bottoms, color=color,
               edgecolor="white", linewidth=0.4, zorder=3, label=cl)
        bottoms += P[:, ci]

    # Condition strip below the bars.
    unique_conds = list(dict.fromkeys(conds))
    group_colors = ["#6FA8DC", "#E06666", "#93C47D", "#C27BA0",
                    "#FFD966"][: len(unique_conds)]
    cmap_c = {g: c for g, c in zip(unique_conds, group_colors)}
    strip_y = -0.08
    strip_h = 0.05
    for xi, c in enumerate(conds):
        ax.add_patch(mpatches.Rectangle(
            (xi - 0.45, strip_y), 0.90, strip_h,
            facecolor=cmap_c[c], edgecolor="white", linewidth=0.3,
            transform=ax.get_xaxis_transform(), clip_on=False, zorder=3,
        ))
    # Label groups at centroid.
    pos_by_group: dict[str, list[int]] = {}
    for xi, c in enumerate(conds):
        pos_by_group.setdefault(c, []).append(xi)
    for g, positions in pos_by_group.items():
        ax.text(float(np.mean(positions)), strip_y - 0.04, g,
                transform=ax.get_xaxis_transform(),
                ha="center", va="top", fontsize=6.4,
                color="#333333", fontweight="bold",
                clip_on=False)

    ax.set_xlim(-0.5, len(samples) - 0.5)
    ax.set_ylim(0, 1.0)
    ax.set_xticks(x)
    ax.set_xticklabels(samples, rotation=45, ha="right", fontsize=6.4)
    ax.set_ylabel("proportion")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.4, frameon=False, loc="center left",
              bbox_to_anchor=(1.02, 0.5), handlelength=1.2,
              title="cluster", title_fontsize=6.4)
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
