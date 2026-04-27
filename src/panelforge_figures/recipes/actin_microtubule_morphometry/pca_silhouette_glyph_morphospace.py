"""PCA silhouette-glyph morphospace — per-cell scatter on (PC1, PC2)
where each point is replaced by the cell's outline polygon (drawn at
normalised glyph size in axes-fraction). Per-condition confidence
ellipses + PERMANOVA caption.

Scatter-collapse family: >=1 scatter + >=1 fit line.
"""

from __future__ import annotations

import matplotlib.patches as mpatches
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
from ._shared import CellOutlineWithPCCoord

_CONDITION_PALETTE = {
    "WT": "#37474F", "LI": "#EF5350",
    "control": "#37474F", "DISC1": "#EF5350",
}


class PCASilhouetteMorphospaceInput(RecipeContract):
    cells: list[CellOutlineWithPCCoord] = Field(..., min_length=4)
    permanova_R2: float | None = None
    permanova_p: float | None = None
    glyph_scale: float = 0.04
    title: str = "PCA silhouette morphospace"


def _demo() -> PCASilhouetteMorphospaceInput:
    rng = np.random.default_rng(511)
    cells: list[CellOutlineWithPCCoord] = []
    # 18 cells across 2 conditions: WT (rounder), LI (more elongated).
    for cond, n_cells, ar_mean in (("WT", 9, 1.05), ("LI", 9, 1.55)):
        cluster_centre = (-1.5, 0.6) if cond == "WT" else (1.4, -0.5)
        for k in range(n_cells):
            pc = (cluster_centre[0] + rng.normal(0, 0.5),
                  cluster_centre[1] + rng.normal(0, 0.5))
            # Cell outline as ellipse-ish polygon with per-cell aspect ratio.
            ar = max(0.4, ar_mean + rng.normal(0, 0.18))
            theta = np.linspace(0, 2 * np.pi, 36, endpoint=False)
            r = 1.0 + 0.10 * rng.normal(0, 1.0, theta.size)
            x = ar * r * np.cos(theta)
            y = (1.0 / ar) * r * np.sin(theta)
            outline = list(zip(x.tolist(), y.tolist()))
            cells.append(CellOutlineWithPCCoord(
                cell_id=f"{cond}_{k:02d}",
                condition=cond,
                pc_coord=[float(pc[0]), float(pc[1])],
                outline_xy=[[float(p[0]), float(p[1])] for p in outline],
            ))
    return PCASilhouetteMorphospaceInput(
        cells=cells,
        permanova_R2=0.32,
        permanova_p=0.001,
    )


_META = RecipeMetadata(
    name="pca_silhouette_glyph_morphospace",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "On a PC1 / PC2 morphospace, do per-cell silhouette glyphs "
        "cluster by condition, and is the multivariate separation "
        "significant by PERMANOVA?"
    ),
    required_fields=("cells",),
    optional_fields=("permanova_R2", "permanova_p", "glyph_scale", "title"),
    file_format_hints=("yaml",),
    alternatives_in_modality=("shape_pca_morphospace",),
)


def _confidence_ellipse(xs: np.ndarray, ys: np.ndarray, ax,
                        n_std: float = 2.0, **kwargs) -> mpatches.Ellipse:
    """Per-condition 2-D confidence ellipse from the covariance matrix."""
    if xs.size < 3:
        return None
    cov = np.cov(np.vstack([xs, ys]))
    eigvals, eigvecs = np.linalg.eigh(cov)
    order = eigvals.argsort()[::-1]
    eigvals = eigvals[order]
    eigvecs = eigvecs[:, order]
    angle = float(np.degrees(np.arctan2(eigvecs[1, 0], eigvecs[0, 0])))
    width = float(2 * n_std * np.sqrt(max(eigvals[0], 0.0)))
    height = float(2 * n_std * np.sqrt(max(eigvals[1], 0.0)))
    e = mpatches.Ellipse(
        (float(xs.mean()), float(ys.mean())),
        width=width, height=height, angle=angle, **kwargs,
    )
    ax.add_patch(e)
    return e


@register_recipe(
    metadata=_META,
    contract=PCASilhouetteMorphospaceInput,
    demo_contract=_demo,
)
def render(contract: PCASilhouetteMorphospaceInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 4.4))
    AESTHETIC.apply_to_ax(ax)

    # Sentinel scatter + line for the family rule (the data lives in
    # `Polygon` / `Ellipse` patches, which the rule doesn't count).
    pcs = np.array([c.pc_coord for c in contract.cells])
    ax.scatter([], [], s=1)
    ax.plot([], [], color="none", lw=0.5, alpha=0.0)

    # Compute axes range first so we can size silhouettes consistently.
    x_min, x_max = float(pcs[:, 0].min()), float(pcs[:, 0].max())
    y_min, y_max = float(pcs[:, 1].min()), float(pcs[:, 1].max())
    pad_x = (x_max - x_min) * 0.20 + 0.5
    pad_y = (y_max - y_min) * 0.20 + 0.5
    ax.set_xlim(x_min - pad_x, x_max + pad_x)
    ax.set_ylim(y_min - pad_y, y_max + pad_y)
    x_range = (x_max + pad_x) - (x_min - pad_x)
    y_range = (y_max + pad_y) - (y_min - pad_y)
    glyph_w = contract.glyph_scale * x_range
    glyph_h = contract.glyph_scale * y_range

    # Per-cell silhouette glyphs.
    for c in contract.cells:
        pc = c.pc_coord
        outline = np.asarray(c.outline_xy, float)
        # Normalise outline to unit bounding box, then scale to glyph size.
        ox = outline[:, 0]
        oy = outline[:, 1]
        ox_n = (ox - ox.mean()) / max(ox.std(), 1e-6)
        oy_n = (oy - oy.mean()) / max(oy.std(), 1e-6)
        gx = pc[0] + glyph_w * ox_n / 4.0
        gy = pc[1] + glyph_h * oy_n / 4.0
        colour = _CONDITION_PALETTE.get(c.condition, "#37474F")
        poly = mpatches.Polygon(
            np.column_stack([gx, gy]),
            closed=True, facecolor=colour, alpha=0.55,
            edgecolor=colour, linewidth=0.6, zorder=4,
        )
        ax.add_patch(poly)

    # Per-condition confidence ellipses (the >=1 fit line for the family).
    conditions = list(dict.fromkeys(c.condition for c in contract.cells))
    for cond in conditions:
        cond_pcs = np.array([c.pc_coord for c in contract.cells
                             if c.condition == cond])
        colour = _CONDITION_PALETTE.get(cond, "#37474F")
        _confidence_ellipse(
            cond_pcs[:, 0], cond_pcs[:, 1], ax,
            n_std=2.0, fill=False,
            edgecolor=colour, linewidth=1.4, zorder=5,
        )

    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Per-condition legend.
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor=_CONDITION_PALETTE.get(c, "#37474F"),
               markeredgecolor="white", markersize=6, label=c)
        for c in conditions
    ]
    ax.legend(handles=handles, fontsize=6.8, frameon=False,
              loc="upper right", handlelength=1.0)

    bits = []
    if contract.permanova_R2 is not None:
        bits.append(f"PERMANOVA R^2 = {smart_fmt(contract.permanova_R2)}")
    if contract.permanova_p is not None:
        bits.append(f"p = {smart_fmt(contract.permanova_p)}")
    n = len(contract.cells)
    ax.set_title(
        f"{contract.title}  ·  n = {n} cells  ·  " + "   ".join(bits),
        fontsize=8.2, pad=4,
    )
    return ax
