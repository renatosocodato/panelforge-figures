"""PCA biplot — scores scatter + gene loading arrows."""

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


class PCABiplotInput(RecipeContract):
    pc1: list[float] = Field(...)
    pc2: list[float] = Field(...)
    cluster: list[str] = Field(...)
    loading_names: list[str] = Field(...)
    loading_pc1: list[float] = Field(...)
    loading_pc2: list[float] = Field(...)
    pc1_variance: float = 0.18
    pc2_variance: float = 0.10
    title: str = "PCA biplot"


def _demo() -> PCABiplotInput:
    rng = np.random.default_rng(317)
    clusters = ["ctrl", "treat", "washout"]
    xs, ys, labels = [], [], []
    for c, (cx, cy) in zip(clusters, [(-2, 0), (2, 1), (0, -2)]):
        n = rng.integers(30, 50)
        xs.append(rng.normal(cx, 0.6, n))
        ys.append(rng.normal(cy, 0.6, n))
        labels.extend([c] * n)
    gene_names = ["IL6", "TNF", "Trem2", "P2ry12", "Apoe", "Cst7", "Itgax"]
    loading_pc1 = np.array([0.6, 0.55, -0.45, -0.5, 0.3, 0.4, 0.35])
    loading_pc2 = np.array([0.1, 0.2, 0.5, 0.4, -0.35, -0.3, -0.2])
    return PCABiplotInput(
        pc1=np.concatenate(xs).tolist(),
        pc2=np.concatenate(ys).tolist(),
        cluster=labels,
        loading_names=gene_names,
        loading_pc1=loading_pc1.tolist(),
        loading_pc2=loading_pc2.tolist(),
    )


_META = RecipeMetadata(
    name="pca_biplot_with_loadings",
    modality="single_cell_embeddings",
    family=RecipeFamily.scatter_collapse,
    answers_question="How do samples separate in the first two principal components, and which genes drive each axis?",
    required_fields=("pc1", "pc2", "cluster", "loading_names",
                     "loading_pc1", "loading_pc2"),
    optional_fields=("pc1_variance", "pc2_variance", "title"),
    file_format_hints=("h5ad", "parquet"),
    alternatives_in_modality=("umap_categorical_with_density_contours",),
)


@register_recipe(metadata=_META, contract=PCABiplotInput, demo_contract=_demo)
def render(contract: PCABiplotInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.8))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    x = np.array(contract.pc1, dtype=float)
    y = np.array(contract.pc2, dtype=float)
    labels = np.array(contract.cluster)
    unique = list(dict.fromkeys(labels))

    fallback_colors = [palette.pick("homeostatic"), palette.pick("activated"),
                       palette.pick("proliferative"), palette.pick("surveillant")]
    for i, c in enumerate(unique):
        color = fallback_colors[i % len(fallback_colors)]
        mask = labels == c
        ax.scatter(x[mask], y[mask], s=18, color=color, alpha=0.75,
                   edgecolor="white", linewidth=0.3,
                   label=c, zorder=3)

    # Scale loadings to fit score-space.
    L1 = np.array(contract.loading_pc1, dtype=float)
    L2 = np.array(contract.loading_pc2, dtype=float)
    scale = 0.6 * min(x.max() - x.min(), y.max() - y.min()) / \
        max(float(np.hypot(L1.max(), L2.max())), 1e-9)

    for name, l1, l2 in zip(contract.loading_names, L1, L2):
        ax.annotate(
            "", xy=(l1 * scale, l2 * scale), xytext=(0, 0),
            arrowprops=dict(arrowstyle="-|>", color="#111111", lw=0.8),
            zorder=5,
        )
        ax.text(l1 * scale * 1.08, l2 * scale * 1.08, name,
                ha="center", va="center", fontsize=6.2, color="#111111",
                bbox=dict(boxstyle="round,pad=0.12", fc="white",
                          ec="none", alpha=0.85),
                zorder=6)

    ax.axhline(0, color="#AAAAAA", lw=0.4, zorder=1)
    ax.axvline(0, color="#AAAAAA", lw=0.4, zorder=1)

    ax.set_xlabel(f"PC1 ({100 * contract.pc1_variance:.0f}%)")
    ax.set_ylabel(f"PC2 ({100 * contract.pc2_variance:.0f}%)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.4)

    ax.text(0.01, 0.02,
            f"N samples = {len(labels)}   "
            f"N loadings shown = {len(contract.loading_names)}",
            transform=ax.transAxes, ha="left", va="bottom",
            fontsize=6.2, color="#444444",
            bbox=dict(boxstyle="round,pad=0.16", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=7)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    _ = smart_fmt
    return ax
