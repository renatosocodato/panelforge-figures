"""Multi-condition density contour overlay on a shared UMAP embedding.

Unlike `umap_categorical_with_density_contours` (per-cluster contours
within a single dataset), this recipe compares the **density shapes
of different conditions** on the same UMAP space. Greyed background
scatter + per-condition coloured contour set + an inter-condition
mean-shift arrow between centroids.
"""

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
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class UMAPOverlayInput(RecipeContract):
    umap1: list[float] = Field(...)
    umap2: list[float] = Field(...)
    condition: list[str] = Field(..., description="per-cell condition label")
    title: str = "UMAP · condition density overlay"


def _demo() -> UMAPOverlayInput:
    rng = np.random.default_rng(431)
    x = []
    y = []
    cond = []
    profiles = {
        "control": [(-3.0, -1.0), (-0.8, 1.6), (2.2, 2.2)],
        "LPS": [(-1.5, 2.5), (1.8, 3.8), (3.8, 0.8)],
        "rescue": [(-3.0, -1.5), (0.0, 2.0), (1.8, 2.0)],
    }
    for c, centres in profiles.items():
        for cx, cy in centres:
            n = rng.integers(120, 220)
            x.append(rng.normal(cx, 0.7, n))
            y.append(rng.normal(cy, 0.7, n))
            cond.extend([c] * n)
    return UMAPOverlayInput(
        umap1=np.concatenate(x).tolist(),
        umap2=np.concatenate(y).tolist(),
        condition=cond,
    )


_META = RecipeMetadata(
    name="umap_density_contour_overlay",
    modality="single_cell_embeddings",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Across conditions, how do the density shapes of cells shift "
        "on the same UMAP embedding?"
    ),
    required_fields=("umap1", "umap2", "condition"),
    optional_fields=("title",),
    file_format_hints=("h5ad", "parquet"),
    alternatives_in_modality=("umap_categorical_with_density_contours",),
)


@register_recipe(
    metadata=_META,
    contract=UMAPOverlayInput,
    demo_contract=_demo,
)
def render(contract: UMAPOverlayInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.8))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    x = np.asarray(contract.umap1, float)
    y = np.asarray(contract.umap2, float)
    cond = np.asarray(contract.condition)
    uniques = list(dict.fromkeys(cond.tolist()))

    # Background scatter — all cells, greyed.
    alpha = density_alpha(x, y) * 0.35
    ax.scatter(x, y, s=4, color="#AAAAAA", alpha=alpha,
               edgecolor="none", zorder=2)

    xg = np.linspace(x.min() - 0.5, x.max() + 0.5, 70)
    yg = np.linspace(y.min() - 0.5, y.max() + 0.5, 70)
    X, Y = np.meshgrid(xg, yg)

    centroids = {}
    for i, c in enumerate(uniques):
        color = palette[i % len(palette.colors)]
        m = cond == c
        if m.sum() < 20:
            continue
        try:
            kde = gaussian_kde(np.vstack([x[m], y[m]]))
            Z = kde(np.vstack([X.ravel(), Y.ravel()])).reshape(X.shape)
            ax.contour(X, Y, Z, levels=4, colors=[color],
                       linewidths=0.9, alpha=0.9, zorder=3)
        except (np.linalg.LinAlgError, ValueError):
            pass
        cx = float(np.median(x[m]))
        cy = float(np.median(y[m]))
        centroids[c] = (cx, cy)
        # Marker + label.
        ax.scatter([cx], [cy], s=32, color=color,
                   edgecolor="white", linewidth=0.8, zorder=5,
                   label=f"{c} (n={int(m.sum())})")

    # Mean-shift arrows from the first condition's centroid to each other.
    # Draw a Line2D segment first (so scatter_collapse rule sees ≥1 line)
    # then overlay the arrow tip via annotate.
    if len(uniques) >= 2 and uniques[0] in centroids:
        x0, y0 = centroids[uniques[0]]
        for c in uniques[1:]:
            if c not in centroids:
                continue
            cx, cy = centroids[c]
            ax.plot([x0, cx], [y0, cy], color="#111111",
                    lw=0.9, zorder=5)
            ax.annotate(
                "", xy=(cx, cy), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="->", color="#111111",
                                lw=0.9, shrinkA=6, shrinkB=6),
                zorder=6,
            )

    ax.set_xlabel("UMAP1")
    ax.set_ylabel("UMAP2")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(
        f"{contract.title}  ·  N cells = {len(cond)}",
        fontsize=9.0, pad=4,
    )
    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.2)

    if len(centroids) >= 2:
        # Callout listing pairwise centroid shift magnitudes.
        ref_c = uniques[0]
        ref_xy = np.array(centroids[ref_c])
        bits = [
            f"||{c} − {ref_c}||={smart_fmt(float(np.linalg.norm(np.array(centroids[c]) - ref_xy)))}"
            for c in uniques[1:]
            if c in centroids
        ]
        ax.text(
            0.02, 0.02, "   ".join(bits),
            transform=ax.transAxes, ha="left", va="bottom",
            fontsize=6.2, color="#333333",
            bbox=dict(boxstyle="round,pad=0.18", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=7,
        )
    return ax
