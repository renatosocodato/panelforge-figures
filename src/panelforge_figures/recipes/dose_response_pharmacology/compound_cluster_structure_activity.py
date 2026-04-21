"""Compound clustering + per-cluster mean activity (SAR two-panel)."""

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


class CompoundClusterInput(RecipeContract):
    compound_names: list[str] = Field(..., min_length=4)
    pc1: list[float] = Field(...)
    pc2: list[float] = Field(...)
    cluster: list[int] = Field(...)
    activity: list[float] = Field(..., description="pIC50 / potency per compound")
    title: str = "Compound clustering · SAR"


def _demo() -> CompoundClusterInput:
    rng = np.random.default_rng(607)
    n = 36
    names = [f"C{i+1:02d}" for i in range(n)]
    # Three clusters in PCA space with distinct mean activity.
    centres = [(-2, 1), (0, -2), (3, 2)]
    cluster = []
    pc1 = []
    pc2 = []
    activity = []
    mean_activity = [5.5, 7.2, 6.3]
    for ci, (cx, cy) in enumerate(centres):
        k = n // 3 + (1 if ci == 0 else 0)
        pc1.extend(rng.normal(cx, 0.6, k).tolist())
        pc2.extend(rng.normal(cy, 0.6, k).tolist())
        cluster.extend([ci] * k)
        activity.extend(rng.normal(mean_activity[ci], 0.5, k).tolist())
    return CompoundClusterInput(
        compound_names=names[: len(cluster)],
        pc1=pc1, pc2=pc2, cluster=cluster, activity=activity,
    )


_META = RecipeMetadata(
    name="compound_cluster_structure_activity",
    modality="dose_response_pharmacology",
    family=RecipeFamily.conceptual,
    answers_question=(
        "Cluster compounds by their structural fingerprints; which "
        "cluster has the best mean activity?"
    ),
    required_fields=("compound_names", "pc1", "pc2", "cluster", "activity"),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("ic50_forest_across_compounds",),
)


@register_recipe(
    metadata=_META,
    contract=CompoundClusterInput,
    demo_contract=_demo,
)
def render(contract: CompoundClusterInput, ax=None, **_):
    import matplotlib.patches as mpatches
    import matplotlib.pyplot as plt

    if ax is None:
        fig = plt.figure(figsize=(6.0, 3.6))
        gs = fig.add_gridspec(1, 2, width_ratios=[2.5, 1], wspace=0.20)
        ax_pca = fig.add_subplot(gs[0, 0])
        ax_bar = fig.add_subplot(gs[0, 1])
    else:
        fig = ax.figure
        pos = ax.get_subplotspec()
        ax.remove()
        sub = pos.subgridspec(1, 2, width_ratios=[2.5, 1], wspace=0.20)
        ax_pca = fig.add_subplot(sub[0, 0])
        ax_bar = fig.add_subplot(sub[0, 1])

    for a in (ax_pca, ax_bar):
        AESTHETIC.apply_to_ax(a)

    pc1 = np.asarray(contract.pc1, float)
    pc2 = np.asarray(contract.pc2, float)
    cluster = np.asarray(contract.cluster, int)
    activity = np.asarray(contract.activity, float)

    uniques = sorted(np.unique(cluster).tolist())
    cluster_colors = ["#5E35B1", "#00897B", "#F4511E", "#546E7A",
                      "#AD1457"][: max(len(uniques), 1)]
    cmap_c = dict(zip(uniques, cluster_colors))

    # PCA scatter with cluster-shaded ellipses.
    for ci in uniques:
        mask = cluster == ci
        color = cmap_c[ci]
        ax_pca.scatter(pc1[mask], pc2[mask], s=22, color=color,
                       alpha=0.80, edgecolor="white", linewidth=0.3,
                       zorder=3, label=f"cluster {ci}")
        # Mean marker.
        mx, my = float(pc1[mask].mean()), float(pc2[mask].mean())
        sd = max(float(np.hypot(pc1[mask].std(), pc2[mask].std())), 0.2)
        ax_pca.add_patch(mpatches.Circle(
            (mx, my), sd,
            facecolor=color, edgecolor=color, linewidth=0.8,
            alpha=0.10, zorder=2,
        ))
        ax_pca.scatter([mx], [my], s=58, marker="*", color=color,
                       edgecolor="white", linewidth=0.6, zorder=5)

    ax_pca.set_xlabel("PC1")
    ax_pca.set_ylabel("PC2")
    ax_pca.set_title("Structural PCA", fontsize=8.4, pad=4)
    ax_pca.legend(fontsize=6.4, frameon=False, loc="best",
                  handlelength=1.2)
    ax_pca.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax_pca.set_axisbelow(True)

    # Per-cluster mean activity bars.
    mean_act = [float(activity[cluster == ci].mean()) for ci in uniques]
    sem_act = [
        float(activity[cluster == ci].std() / max(np.sqrt((cluster == ci).sum()), 1))
        for ci in uniques
    ]
    xpos = np.arange(len(uniques))
    for xi, mu, se, ci in zip(xpos, mean_act, sem_act, uniques):
        ax_bar.bar(xi, mu, yerr=se, color=cmap_c[ci], alpha=0.85,
                   capsize=3, edgecolor="white", linewidth=0.5, zorder=3)
        # Value label on top of each bar (also gives the conceptual
        # quality rule the ≥3 text artists it requires).
        ax_bar.text(xi, mu + max(se, 0.05) + 0.1,
                    f"{smart_fmt(mu)}",
                    ha="center", va="bottom", fontsize=6.2,
                    color=cmap_c[ci], zorder=5)
    ax_bar.set_xticks(xpos)
    ax_bar.set_xticklabels([f"c{ci}" for ci in uniques], fontsize=6.8)
    ax_bar.set_ylabel("mean pIC50")
    ax_bar.set_title("Activity by cluster", fontsize=8.4, pad=4)
    ax_bar.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax_bar.set_axisbelow(True)

    # Best-cluster callout.
    best = uniques[int(np.argmax(mean_act))]
    fig.suptitle(
        f"{contract.title}  ·  best cluster: c{best} "
        f"(mean pIC50 = {smart_fmt(float(np.max(mean_act)))})",
        fontsize=8.6, y=1.02,
    )
    return ax_pca
