"""Per-cluster marker genes — z-scored expression heatmap.

Unlike `expression_dotplot_by_cluster` (dot grammar: size ∝ %, colour ∝ mean),
this recipe plots a clean z-scored divergent heatmap with markers
ordered by their cluster of origin and a thin row-cluster annotation
strip on the left.
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


class MarkerHeatmapInput(RecipeContract):
    clusters: list[str] = Field(..., min_length=2)
    genes: list[str] = Field(..., min_length=3)
    origin_cluster: list[str] = Field(
        ..., description="cluster of origin per gene (same length as genes)"
    )
    z_expression: list[list[float]] = Field(
        ..., description="n_genes × n_clusters z-scored expression"
    )
    title: str = "Per-cluster marker heatmap"


def _demo() -> MarkerHeatmapInput:
    rng = np.random.default_rng(829)
    clusters = ["homeostatic", "surveillant", "activated", "DAM", "proliferative"]
    genes_per_cluster = {
        "homeostatic": ["P2ry12", "Tmem119", "Cx3cr1"],
        "surveillant": ["Apoe", "Fcrls", "Csf1r"],
        "activated": ["Cd74", "H2-Aa", "Itgax"],
        "DAM": ["Cst7", "Lpl", "Trem2"],
        "proliferative": ["Mki67", "Top2a", "Ki67"],
    }
    genes, origins = [], []
    for c in clusters:
        for g in genes_per_cluster[c]:
            genes.append(g)
            origins.append(c)
    Z = rng.normal(0, 0.5, (len(genes), len(clusters)))
    # Boost expression of each gene in its origin cluster.
    for gi, og in enumerate(origins):
        ci = clusters.index(og)
        Z[gi, ci] += rng.uniform(1.8, 2.8)
    return MarkerHeatmapInput(
        clusters=clusters,
        genes=genes,
        origin_cluster=origins,
        z_expression=Z.tolist(),
    )


_META = RecipeMetadata(
    name="per_cluster_marker_heatmap",
    modality="single_cell_embeddings",
    family=RecipeFamily.heatmap,
    answers_question=(
        "For the top-N marker genes per cluster, what is the z-scored "
        "expression pattern across clusters?"
    ),
    required_fields=(
        "clusters", "genes", "origin_cluster", "z_expression",
    ),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet", "npz"),
    alternatives_in_modality=("expression_dotplot_by_cluster",),
)


@register_recipe(
    metadata=_META,
    contract=MarkerHeatmapInput,
    demo_contract=_demo,
)
def render(contract: MarkerHeatmapInput, ax=None, **_):
    import matplotlib as mpl
    import matplotlib.patches as mpatches

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 4.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    clusters = contract.clusters
    genes = contract.genes
    origins = contract.origin_cluster
    Z = np.asarray(contract.z_expression, float)
    n_g, n_c = Z.shape
    v_hi = float(max(abs(Z).max(), 1e-9))

    cmap = mpl.colormaps["RdBu_r"]
    im = ax.imshow(Z, cmap=cmap, vmin=-v_hi, vmax=v_hi,
                   aspect="auto", interpolation="nearest")

    ax.set_xticks(range(n_c))
    ax.set_xticklabels(clusters, rotation=35, ha="right", fontsize=6.8)
    ax.set_yticks(range(n_g))
    ax.set_yticklabels(genes, fontsize=6.4)

    # Origin-cluster annotation strip on the left.
    for gi, og in enumerate(origins):
        color = (palette.pick(og) if og in palette.semantic
                 else palette[clusters.index(og) % len(palette.colors)])
        ax.add_patch(mpatches.Rectangle(
            (-0.62, gi - 0.48), 0.15, 0.96,
            facecolor=color, edgecolor="white", linewidth=0.3,
            clip_on=False, zorder=4,
        ))

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.040, pad=0.03)
    cbar.set_label("z(expr)", fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    # Top-marker callout.
    top_i, top_j = np.unravel_index(int(np.argmax(Z)), Z.shape)
    ax.set_title(
        f"{contract.title}  ·  top marker: "
        f"{genes[top_i]} in {clusters[top_j]} "
        f"(z={smart_fmt(float(Z[top_i, top_j]))})",
        fontsize=8.4, pad=4,
    )
    return ax
