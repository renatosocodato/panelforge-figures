"""Rare-population spotlight UMAP — bulk greyed, rare cells highlighted.

All non-rare cells are greyed to low alpha; the rare population is
plotted with strong colour, a convex hull outline, a median marker and
a % callout.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

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


class RarePopUMAPInput(RecipeContract):
    umap1: list[float] = Field(...)
    umap2: list[float] = Field(...)
    cluster: list[str] = Field(...)
    rare_cluster: str = Field(..., description="the cluster label to spotlight")
    title: str = "Rare-population spotlight"


def _demo() -> RarePopUMAPInput:
    rng = np.random.default_rng(541)
    clusters = []
    xs = []
    ys = []
    centers = [
        ("homeostatic", -4, 0, 0.8, 350),
        ("surveillant", -1, 3, 0.8, 320),
        ("activated", 2, 4, 0.8, 300),
        ("DAM", 4, -1, 0.8, 260),
        ("proliferative", -2, -4, 0.5, 30),  # rare
    ]
    for c, cx, cy, s, n in centers:
        xs.append(rng.normal(cx, s, n))
        ys.append(rng.normal(cy, s, n))
        clusters.extend([c] * n)
    return RarePopUMAPInput(
        umap1=np.concatenate(xs).tolist(),
        umap2=np.concatenate(ys).tolist(),
        cluster=clusters,
        rare_cluster="proliferative",
    )


_META = RecipeMetadata(
    name="rare_population_highlighted_umap",
    modality="single_cell_embeddings",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Where in UMAP space does a rare population sit, compared to "
        "the bulk?"
    ),
    required_fields=("umap1", "umap2", "cluster", "rare_cluster"),
    optional_fields=("title",),
    file_format_hints=("h5ad", "parquet"),
    alternatives_in_modality=("umap_categorical_with_density_contours",),
)


@register_recipe(
    metadata=_META,
    contract=RarePopUMAPInput,
    demo_contract=_demo,
)
def render(contract: RarePopUMAPInput, ax=None, **_):
    from scipy.spatial import ConvexHull

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.6))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    x = np.asarray(contract.umap1, float)
    y = np.asarray(contract.umap2, float)
    cl = np.asarray(contract.cluster)
    rare = contract.rare_cluster
    rare_mask = cl == rare
    bulk_mask = ~rare_mask

    # Bulk greyed.
    alpha_bg = density_alpha(x[bulk_mask], y[bulk_mask]) * 0.40 if bulk_mask.any() else np.array([])
    ax.scatter(x[bulk_mask], y[bulk_mask], s=4, color="#888888",
               alpha=alpha_bg, edgecolor="none", zorder=2,
               label=f"bulk (n={int(bulk_mask.sum())})")

    rare_color = (palette.pick(rare) if rare in palette.semantic
                  else "#D32F2F")
    ax.scatter(x[rare_mask], y[rare_mask], s=22, color=rare_color,
               alpha=0.90, edgecolor="white", linewidth=0.5, zorder=4,
               label=f"{rare} (n={int(rare_mask.sum())})")

    # Convex hull + median marker.
    if rare_mask.sum() >= 3:
        pts = np.column_stack([x[rare_mask], y[rare_mask]])
        try:
            hull = ConvexHull(pts)
            verts = pts[hull.vertices]
            verts = np.vstack([verts, verts[0]])
            ax.plot(verts[:, 0], verts[:, 1], color=rare_color,
                    lw=1.1, alpha=0.85, zorder=5)
        except Exception:
            pass
    mx = float(np.median(x[rare_mask])) if rare_mask.any() else 0.0
    my = float(np.median(y[rare_mask])) if rare_mask.any() else 0.0
    ax.scatter([mx], [my], s=60, marker="*", color=rare_color,
               edgecolor="white", linewidth=0.8, zorder=6)

    # % callout.
    pct = 100.0 * rare_mask.sum() / max(cl.size, 1)
    ax.text(0.99, 0.97,
            f"{rare}: {int(rare_mask.sum())} / {cl.size} cells "
            f"({smart_fmt(pct)}%)",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=6.8, color="#111111",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec=rare_color, lw=0.8, alpha=0.95),
            zorder=7)

    ax.set_xlabel("UMAP1")
    ax.set_ylabel("UMAP2")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="lower right",
              handlelength=1.4)
    return ax
