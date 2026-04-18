"""UMAP colored continuously by gene expression (viridis)."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    density_alpha,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class UMAPContinuousInput(RecipeContract):
    umap1: list[float] = Field(...)
    umap2: list[float] = Field(...)
    expression: list[float] = Field(..., description="per-cell expression value")
    gene_name: str = "gene"
    title: str = "UMAP · gene expression"


def _demo() -> UMAPContinuousInput:
    rng = np.random.default_rng(307)
    n = 1500
    # UMAP with a gradient.
    u1 = rng.uniform(-5, 5, n)
    u2 = rng.uniform(-5, 5, n)
    # Expression peaks in one quadrant.
    expr = np.clip(
        0.8 * np.exp(-((u1 - 2) ** 2 + (u2 + 1) ** 2) / 4)
        + rng.normal(0, 0.05, n),
        0, None,
    )
    return UMAPContinuousInput(
        umap1=u1.tolist(),
        umap2=u2.tolist(),
        expression=expr.tolist(),
        gene_name="Tmem119",
    )


_META = RecipeMetadata(
    name="umap_continuous_expression",
    modality="single_cell_embeddings",
    family=RecipeFamily.heatmap,
    answers_question="Where in UMAP space is a given gene expressed, and how strongly?",
    required_fields=("umap1", "umap2", "expression"),
    optional_fields=("gene_name", "title"),
    file_format_hints=("h5ad", "parquet"),
    alternatives_in_modality=("umap_categorical_with_density_contours",),
)


@register_recipe(metadata=_META, contract=UMAPContinuousInput, demo_contract=_demo)
def render(contract: UMAPContinuousInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.6, 3.4))
    AESTHETIC.apply_to_ax(ax)

    x = np.array(contract.umap1, dtype=float)
    y = np.array(contract.umap2, dtype=float)
    e = np.array(contract.expression, dtype=float)

    alpha = density_alpha(x, y, alpha_min=0.25, alpha_max=0.85)
    sc = ax.scatter(x, y, s=8, c=e, cmap=AESTHETIC.continuous_cmap,
                    alpha=alpha, edgecolor="none", zorder=3)

    ax.set_xlabel("UMAP1")
    ax.set_ylabel("UMAP2")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(f"{contract.title} · {contract.gene_name}",
                 fontsize=9.0, pad=4)

    cbar = ax.figure.colorbar(sc, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(f"{contract.gene_name} expression", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)

    ax.text(0.01, 0.02,
            f"N = {len(e)}   max expr = {smart_fmt(float(e.max()))}\n"
            f"% cells > 0: {100 * (e > 0).mean():.0f}%",
            transform=ax.transAxes, ha="left", va="bottom",
            fontsize=6.4, color="#444444",
            bbox=dict(boxstyle="round,pad=0.18", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)
    return ax
