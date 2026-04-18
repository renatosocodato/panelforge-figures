"""UMAP with categorical clusters + KDE density contours per cluster."""

from __future__ import annotations

import numpy as np
from pydantic import Field
from scipy.stats import gaussian_kde

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    density_alpha,
    get_palette,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class UMAPCategoricalInput(RecipeContract):
    umap1: list[float] = Field(...)
    umap2: list[float] = Field(...)
    cluster: list[str] = Field(..., description="per-cell cluster label")
    title: str = "UMAP · clusters"


def _demo() -> UMAPCategoricalInput:
    rng = np.random.default_rng(301)
    clusters = ["homeostatic", "surveillant", "activated", "DAM", "proliferative"]
    xs = []
    ys = []
    labels = []
    centers = [(-4, 0), (-1, 3), (2, 4), (4, -1), (-2, -4)]
    for c, (cx, cy) in zip(clusters, centers):
        n = rng.integers(180, 280)
        xs.append(rng.normal(cx, 0.8, n))
        ys.append(rng.normal(cy, 0.8, n))
        labels.extend([c] * n)
    return UMAPCategoricalInput(
        umap1=np.concatenate(xs).tolist(),
        umap2=np.concatenate(ys).tolist(),
        cluster=labels,
    )


_META = RecipeMetadata(
    name="umap_categorical_with_density_contours",
    modality="single_cell_embeddings",
    family=RecipeFamily.scatter_collapse,
    answers_question="Where do single-cell clusters land in UMAP space, and how tightly are they concentrated?",
    required_fields=("umap1", "umap2", "cluster"),
    optional_fields=("title",),
    file_format_hints=("h5ad", "parquet"),
    alternatives_in_modality=("umap_continuous_expression",),
)


@register_recipe(metadata=_META, contract=UMAPCategoricalInput, demo_contract=_demo)
def render(contract: UMAPCategoricalInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.6))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    x = np.array(contract.umap1, dtype=float)
    y = np.array(contract.umap2, dtype=float)
    labels = np.array(contract.cluster)
    unique = list(dict.fromkeys(labels))

    # Background scatter alpha by density.
    alpha = density_alpha(x, y)
    # Per-cluster color mapping.
    for c in unique:
        color = palette.pick(c) if c in palette.semantic else palette[0]
        mask = labels == c
        ax.scatter(x[mask], y[mask], s=5, color=color, alpha=alpha[mask],
                   edgecolor="none", zorder=2)

        # KDE contours for each cluster.
        if mask.sum() >= 20:
            xy = np.vstack([x[mask], y[mask]])
            try:
                kde = gaussian_kde(xy)
                xg = np.linspace(x.min(), x.max(), 60)
                yg = np.linspace(y.min(), y.max(), 60)
                X, Y = np.meshgrid(xg, yg)
                Z = kde(np.vstack([X.ravel(), Y.ravel()])).reshape(X.shape)
                ax.contour(X, Y, Z, levels=3, colors=[color],
                           linewidths=0.6, alpha=0.7, zorder=3)
                # Label at cluster centroid.
                cx, cy = np.mean(x[mask]), np.mean(y[mask])
                ax.text(cx, cy, c, color=color,
                        ha="center", va="center", fontsize=6.8,
                        bbox=dict(boxstyle="round,pad=0.14", fc="white",
                                  ec="none", alpha=0.85),
                        zorder=5)
            except Exception:
                pass

    # Thin dotted path connecting cluster centroids — a visual aid AND ensures
    # at least one Line2D on the axis for downstream quality checks.
    centroids = []
    for c in unique:
        mask = labels == c
        if mask.sum() >= 20:
            centroids.append((float(np.mean(x[mask])), float(np.mean(y[mask]))))
    if len(centroids) >= 2:
        ax.plot([p[0] for p in centroids], [p[1] for p in centroids],
                color="#AAAAAA", lw=0.5, ls=":", alpha=0.5, zorder=1)

    ax.set_xlabel("UMAP1")
    ax.set_ylabel("UMAP2")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    # Cell count.
    ax.text(0.99, 0.02,
            f"N cells = {len(labels)}",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6.4, color="#444444",
            bbox=dict(boxstyle="round,pad=0.18", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)
    return ax
