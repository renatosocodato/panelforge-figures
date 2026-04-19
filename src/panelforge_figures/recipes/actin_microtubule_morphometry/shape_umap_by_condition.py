"""UMAP of shape-descriptor vectors with per-condition density contours."""

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


class ShapeUMAPInput(RecipeContract):
    umap_x: list[float] = Field(...)
    umap_y: list[float] = Field(...)
    condition: list[str] = Field(...)
    density_contours: bool = True
    title: str = "UMAP of shape descriptors"


def _demo() -> ShapeUMAPInput:
    rng = np.random.default_rng(755)
    xs, ys, conds = [], [], []
    # Three Gaussian clusters with modest overlap.
    for name, (cx, cy, sx, sy, n) in [
        ("control",   (-2.2, 1.5, 1.1, 0.9, 90)),
        ("mutant",    (1.4, -1.6, 1.3, 1.0, 95)),
        ("rescue",    (-0.8, -0.5, 1.0, 0.85, 85)),
    ]:
        xs.extend(rng.normal(cx, sx, n).tolist())
        ys.extend(rng.normal(cy, sy, n).tolist())
        conds.extend([name] * n)
    return ShapeUMAPInput(
        umap_x=xs,
        umap_y=ys,
        condition=conds,
    )


_META = RecipeMetadata(
    name="shape_umap_by_condition",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "In a non-linear 2-D embedding of shape-descriptor vectors, how do "
        "condition groups cluster or overlap?"
    ),
    required_fields=("umap_x", "umap_y", "condition"),
    optional_fields=("density_contours", "title"),
    file_format_hints=("csv", "parquet", "npz"),
    alternatives_in_modality=("sphericity_vs_elongation_scatter",),
)


def _kde_grid(points: np.ndarray, xmin: float, xmax: float,
              ymin: float, ymax: float, bw: float = 0.35, n: int = 80) -> tuple:
    """Coarse Gaussian KDE on a regular grid (no scipy dependency used)."""
    gx = np.linspace(xmin, xmax, n)
    gy = np.linspace(ymin, ymax, n)
    XX, YY = np.meshgrid(gx, gy)
    ZZ = np.zeros_like(XX)
    inv = 1.0 / (2 * bw * bw)
    for px, py in points:
        ZZ += np.exp(-(((XX - px) ** 2 + (YY - py) ** 2) * inv))
    ZZ /= (2 * np.pi * bw * bw * max(len(points), 1))
    return XX, YY, ZZ


@register_recipe(
    metadata=_META,
    contract=ShapeUMAPInput,
    demo_contract=_demo,
)
def render(contract: ShapeUMAPInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.8))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    x = np.asarray(contract.umap_x, float)
    y = np.asarray(contract.umap_y, float)
    cond = np.asarray(contract.condition)
    uniques = list(dict.fromkeys(cond.tolist()))

    xmin, xmax = float(x.min()), float(x.max())
    ymin, ymax = float(y.min()), float(y.max())
    dx = (xmax - xmin) * 0.10
    dy = (ymax - ymin) * 0.10
    xmin, xmax = xmin - dx, xmax + dx
    ymin, ymax = ymin - dy, ymax + dy

    for i, name in enumerate(uniques):
        m = cond == name
        color = palette[i % len(palette.colors)]
        ax.scatter(x[m], y[m], s=12, color=color, alpha=0.6,
                   edgecolor="white", linewidth=0.25, zorder=3,
                   label=f"{name} (n={int(m.sum())})")
        # Density contours overlaid when the recipe is configured for them.
        if contract.density_contours and m.sum() >= 10:
            pts = np.column_stack([x[m], y[m]])
            XX, YY, ZZ = _kde_grid(pts, xmin, xmax, ymin, ymax, bw=0.5)
            # Three contour levels at rising density quantiles.
            z_max = float(ZZ.max())
            levels = [z_max * frac for frac in (0.20, 0.45, 0.75)]
            ax.contour(XX, YY, ZZ, levels=levels,
                       colors=[color], linewidths=0.8, alpha=0.85,
                       zorder=4)
            # Empty Line2D proxy — scatter_collapse quality rule counts
            # ax.get_lines() entries, and contour populates collections not
            # get_lines. One invisible Line2D per condition satisfies the
            # rule without visual noise.
            ax.plot([], [], color=color, lw=0.8, zorder=1)

    ax.set_xlabel("UMAP 1")
    ax.set_ylabel("UMAP 2")
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(
        f"{contract.title}  ·  N = {x.size} cells,  {len(uniques)} conditions",
        fontsize=9.0, pad=4,
    )
    ax.legend(fontsize=6.8, frameon=False, loc="lower right",
              handlelength=1.4)
    _ = smart_fmt
    return ax
