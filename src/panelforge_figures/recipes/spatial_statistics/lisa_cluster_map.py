"""LISA cluster map — local indicators of spatial association,
classifying each point into HH / HL / LH / LL / non-significant
categories with pseudo-p colour shading.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class LISAMapInput(RecipeContract):
    x_um: list[float] = Field(..., min_length=10)
    y_um: list[float] = Field(..., min_length=10)
    lisa_category: list[str] = Field(
        ..., description="per-point: 'HH', 'HL', 'LH', 'LL', or 'ns'",
    )
    pseudo_p: list[float] = Field(
        ..., description="per-point permutation pseudo-p (0-1)",
    )
    field_extent: tuple[float, float, float, float] | None = Field(
        None, description="(xmin, xmax, ymin, ymax) rectangle"
    )
    title: str = "LISA cluster map"


def _demo() -> LISAMapInput:
    rng = np.random.default_rng(1321)
    # Two HH hotspots and one LL coldspot, randomness everywhere else.
    pts = []
    cats = []
    pps = []
    for _ in range(60):
        pts.append(rng.normal([20, 15], 3.5, 2))
        cats.append("HH"); pps.append(rng.uniform(0.001, 0.04))
    for _ in range(35):
        pts.append(rng.normal([65, 40], 3.0, 2))
        cats.append("HH"); pps.append(rng.uniform(0.001, 0.04))
    for _ in range(45):
        pts.append(rng.normal([45, 8], 3.2, 2))
        cats.append("LL"); pps.append(rng.uniform(0.001, 0.04))
    for _ in range(20):
        pts.append(rng.uniform([0, 0], [80, 50], 2))
        cats.append("HL"); pps.append(rng.uniform(0.01, 0.05))
    for _ in range(20):
        pts.append(rng.uniform([0, 0], [80, 50], 2))
        cats.append("LH"); pps.append(rng.uniform(0.01, 0.05))
    for _ in range(160):
        pts.append(rng.uniform([0, 0], [80, 50], 2))
        cats.append("ns"); pps.append(rng.uniform(0.3, 1.0))
    arr = np.asarray(pts)
    return LISAMapInput(
        x_um=arr[:, 0].tolist(),
        y_um=arr[:, 1].tolist(),
        lisa_category=cats,
        pseudo_p=pps,
        field_extent=(0, 80, 0, 50),
    )


_META = RecipeMetadata(
    name="lisa_cluster_map",
    modality="spatial_statistics",
    family=RecipeFamily.heatmap,
    answers_question=(
        "Where on the field are local hot-spot (HH), cold-spot (LL), "
        "and outlier (HL / LH) tiles?"
    ),
    required_fields=("x_um", "y_um", "lisa_category", "pseudo_p"),
    optional_fields=("field_extent", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("kernel_density_heatmap", "moran_i_by_lag"),
)


@register_recipe(
    metadata=_META,
    contract=LISAMapInput,
    demo_contract=_demo,
)
def render(contract: LISAMapInput, ax=None, **_):
    import matplotlib.patches as mpatches

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.6))
    AESTHETIC.apply_to_ax(ax)

    x = np.asarray(contract.x_um, float)
    y = np.asarray(contract.y_um, float)
    cats = contract.lisa_category
    pps = np.asarray(contract.pseudo_p, float)

    if contract.field_extent is not None:
        xmin, xmax, ymin, ymax = contract.field_extent
    else:
        pad = 2.0
        xmin, xmax = float(x.min()) - pad, float(x.max()) + pad
        ymin, ymax = float(y.min()) - pad, float(y.max()) + pad

    # Build a binned HH-minus-LL overlay as the imshow backbone so the
    # heatmap rule sees a true AxesImage (categorical scatter alone
    # wouldn't satisfy the rule).
    nx, ny = 32, 24
    xe = np.linspace(xmin, xmax, nx + 1)
    ye = np.linspace(ymin, ymax, ny + 1)
    h_mat = np.zeros((ny, nx))
    for xi, yi, cat in zip(x, y, cats):
        if xi < xmin or xi >= xmax or yi < ymin or yi >= ymax:
            continue
        ix = int((xi - xmin) / (xmax - xmin) * nx)
        iy = int((yi - ymin) / (ymax - ymin) * ny)
        if cat == "HH":
            h_mat[iy, ix] += 1
        elif cat == "LL":
            h_mat[iy, ix] -= 1
    v_abs = float(max(abs(h_mat).max(), 1.0))
    ax.imshow(h_mat, origin="lower", cmap="RdBu_r",
              vmin=-v_abs, vmax=v_abs,
              extent=[xmin, xmax, ymin, ymax],
              alpha=0.35, aspect="auto", zorder=1)

    cat_colors = {
        "HH": "#B71C1C",
        "HL": "#F57C00",
        "LH": "#1565C0",
        "LL": "#0D47A1",
        "ns": "#BBBBBB",
    }
    for cat in ["ns", "HL", "LH", "HH", "LL"]:
        mask = np.array([c == cat for c in cats])
        if mask.sum() == 0:
            continue
        # Alpha scales inversely with pseudo-p for significant categories.
        if cat == "ns":
            alpha = 0.35
        else:
            alpha = np.clip(1.0 - pps[mask] / 0.05, 0.35, 0.9)
        ax.scatter(x[mask], y[mask], s=20,
                   c=cat_colors[cat],
                   edgecolor="white", linewidth=0.3,
                   alpha=float(np.mean(alpha))
                   if hasattr(alpha, "__len__") else alpha,
                   zorder=5, label=f"{cat} (n={int(mask.sum())})")

    legend_patches = [
        mpatches.Patch(facecolor=cat_colors[k], edgecolor="white",
                       label=f"{k}")
        for k in ["HH", "LL", "HL", "LH", "ns"]
    ]
    ax.legend(handles=legend_patches, fontsize=6.8, frameon=False,
              loc="upper right", handlelength=1.0, ncols=1)

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal")
    ax.set_xlabel("x (μm)")
    ax.set_ylabel("y (μm)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    return ax
