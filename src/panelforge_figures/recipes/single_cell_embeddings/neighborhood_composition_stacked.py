"""Neighborhood composition — stacked bars of cluster composition per condition."""

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


class NeighborhoodCompInput(RecipeContract):
    conditions: list[str]
    clusters: list[str]
    fractions: list[list[float]] = Field(
        ..., description="fractions[cond][cluster] summing to 1 per condition"
    )
    title: str = "Cluster composition by condition"


def _demo() -> NeighborhoodCompInput:
    rng = np.random.default_rng(323)
    conditions = ["young ctrl", "aged ctrl", "young LPS", "aged LPS"]
    clusters = ["homeostatic", "surveillant", "activated", "DAM", "proliferative"]
    fractions = []
    for _ in conditions:
        raw = rng.dirichlet(np.array([3, 3, 2, 2, 1.5]))
        fractions.append(raw.tolist())
    # Shift aged LPS toward activated + DAM.
    fractions[3] = np.array([0.1, 0.15, 0.35, 0.30, 0.10]).tolist()
    return NeighborhoodCompInput(
        conditions=conditions,
        clusters=clusters,
        fractions=fractions,
    )


_META = RecipeMetadata(
    name="neighborhood_composition_stacked",
    modality="single_cell_embeddings",
    family=RecipeFamily.matrix,
    answers_question="How do cluster fractions change across experimental conditions?",
    required_fields=("conditions", "clusters", "fractions"),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("umap_categorical_with_density_contours",),
)


@register_recipe(metadata=_META, contract=NeighborhoodCompInput, demo_contract=_demo)
def render(contract: NeighborhoodCompInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    F = np.array(contract.fractions, dtype=float)
    # Normalize rows to 1 just in case.
    F = F / np.maximum(F.sum(axis=1, keepdims=True), 1e-12)

    colors = [
        palette.pick(c) if c in palette.semantic else palette[i]
        for i, c in enumerate(contract.clusters)
    ]

    # Stacked horizontal bars.
    y = np.arange(len(contract.conditions))
    left = np.zeros(len(contract.conditions))
    for ci, c in enumerate(contract.clusters):
        w = F[:, ci]
        ax.barh(y, w, left=left, color=colors[ci], alpha=0.9,
                edgecolor="white", linewidth=0.6, zorder=3,
                label=c)
        # Percent label only if segment is wide enough.
        for yi, li, wi in zip(y, left, w):
            if wi > 0.08:
                ax.text(li + wi / 2, yi, f"{wi*100:.0f}%",
                        ha="center", va="center",
                        color="white", fontsize=6.0)
        left += w

    ax.set_yticks(y)
    ax.set_yticklabels(contract.conditions, fontsize=7.0)
    ax.set_xlim(0, 1)
    ax.set_xticks(np.linspace(0, 1, 6))
    ax.set_xticklabels([f"{int(p)}%" for p in np.linspace(0, 100, 6)],
                       fontsize=6.8)
    ax.set_xlabel("fraction")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15),
              ncol=len(contract.clusters), fontsize=6.6, frameon=False,
              handlelength=1.0, columnspacing=0.8)
    for s in ("left",):
        ax.spines[s].set_visible(False)
    return ax
