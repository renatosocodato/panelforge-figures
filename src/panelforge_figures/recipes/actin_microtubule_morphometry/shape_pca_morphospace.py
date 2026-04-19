"""Shape-descriptor PCA morphospace — scatter + per-condition convex hulls + loading arrows."""

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


class ShapePCAInput(RecipeContract):
    pc1: list[float] = Field(...)
    pc2: list[float] = Field(...)
    condition: list[str] = Field(...)
    loadings: dict[str, tuple[float, float]] | None = Field(
        None, description="descriptor name → (PC1 loading, PC2 loading)"
    )
    explained_variance: tuple[float, float] = Field(
        default=(0.40, 0.22),
        description="(PC1_var_explained, PC2_var_explained) in [0, 1]",
    )
    title: str = "Shape-descriptor PCA morphospace"


def _demo() -> ShapePCAInput:
    rng = np.random.default_rng(835)
    xs, ys, conds = [], [], []
    for name, (cx, cy, sx, sy, n) in [
        ("control",   (-1.8, 1.0, 0.9, 0.7, 80)),
        ("mutant",    (1.6, -1.1, 1.1, 0.8, 80)),
        ("rescue",    (-0.5, -0.3, 0.85, 0.75, 75)),
    ]:
        xs.extend(rng.normal(cx, sx, n).tolist())
        ys.extend(rng.normal(cy, sy, n).tolist())
        conds.extend([name] * n)
    loadings = {
        "area":        (0.55, 0.30),
        "perimeter":   (0.60, 0.12),
        "sphericity":  (-0.48, 0.45),
        "elongation":  (0.42, -0.52),
        "solidity":    (-0.32, 0.60),
    }
    return ShapePCAInput(
        pc1=xs,
        pc2=ys,
        condition=conds,
        loadings=loadings,
        explained_variance=(0.44, 0.22),
    )


_META = RecipeMetadata(
    name="shape_pca_morphospace",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "In a linear PCA embedding of shape-descriptor vectors, how do "
        "condition groups cluster, and which descriptors drive the axes?"
    ),
    required_fields=("pc1", "pc2", "condition"),
    optional_fields=("loadings", "explained_variance", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=(
        "shape_umap_by_condition",
        "shape_descriptor_scatter_matrix",
    ),
)


@register_recipe(
    metadata=_META,
    contract=ShapePCAInput,
    demo_contract=_demo,
)
def render(contract: ShapePCAInput, ax=None, **_):
    from scipy.spatial import ConvexHull

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 4.0))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    x = np.asarray(contract.pc1, float)
    y = np.asarray(contract.pc2, float)
    cond = np.asarray(contract.condition)
    uniques = list(dict.fromkeys(cond.tolist()))

    # Per-condition scatter + convex hull.
    for i, name in enumerate(uniques):
        m = cond == name
        color = palette[i % len(palette.colors)]
        ax.scatter(x[m], y[m], s=14, color=color, alpha=0.65,
                   edgecolor="white", linewidth=0.3, zorder=3,
                   label=f"{name} (n={int(m.sum())})")
        pts = np.column_stack([x[m], y[m]])
        if pts.shape[0] >= 3:
            try:
                hull = ConvexHull(pts)
                verts = pts[hull.vertices]
                verts = np.vstack([verts, verts[0]])
                ax.plot(verts[:, 0], verts[:, 1], color=color,
                        lw=1.1, alpha=0.75, zorder=4)
            except Exception:
                pass

    # Origin axes.
    ax.axhline(0, color="#BBBBBB", lw=0.5, zorder=1)
    ax.axvline(0, color="#BBBBBB", lw=0.5, zorder=1)

    # PC-loading arrows (biplot overlay).
    if contract.loadings:
        xr = float(max(abs(x.min()), abs(x.max())))
        yr = float(max(abs(y.min()), abs(y.max())))
        scale = 0.75 * min(xr, yr)
        for name, (lx, ly) in contract.loadings.items():
            ax.annotate(
                "",
                xy=(lx * scale, ly * scale),
                xytext=(0, 0),
                arrowprops=dict(arrowstyle="->", color="#111111",
                                lw=1.1, shrinkA=0, shrinkB=0),
                zorder=5,
            )
            ax.text(lx * scale * 1.08, ly * scale * 1.08, name,
                    ha="center", va="center", fontsize=6.4, color="#111111",
                    bbox=dict(boxstyle="round,pad=0.12", fc="white",
                              ec="none", alpha=0.88),
                    zorder=6)

    pc1_var, pc2_var = contract.explained_variance
    ax.set_xlabel(f"PC1 ({smart_fmt(pc1_var * 100)}%)")
    ax.set_ylabel(f"PC2 ({smart_fmt(pc2_var * 100)}%)")
    total_var = (pc1_var + pc2_var) * 100
    ax.set_title(
        f"{contract.title}  ·  {smart_fmt(total_var)}% cumulative var",
        fontsize=9.0, pad=4,
    )
    ax.legend(fontsize=6.6, frameon=False, loc="lower right",
              handlelength=1.4)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
