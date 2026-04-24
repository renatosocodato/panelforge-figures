"""Surface electrostatic-potential colormap — 2-D projection of
molecular-surface electrostatic potential (kT/e) with RdBu_r colormap
and charge-patch summary.
"""

from __future__ import annotations

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


class SurfaceElectrostaticsInput(RecipeContract):
    x_edges: list[float] = Field(..., min_length=3,
                                 description="x-grid edges (Å)")
    y_edges: list[float] = Field(..., min_length=3,
                                 description="y-grid edges (Å)")
    potential: list[list[float]] = Field(
        ...,
        description="(n_y × n_x) electrostatic potential grid (kT/e)",
    )
    mask: list[list[bool]] | None = Field(
        None,
        description="optional boolean mask; True = protein surface, "
                    "False = solvent / outside",
    )
    title: str = "Surface electrostatic potential"


def _demo() -> SurfaceElectrostaticsInput:
    rng = np.random.default_rng(3131)
    nx, ny = 60, 50
    xe = np.linspace(-40, 40, nx + 1)
    ye = np.linspace(-30, 30, ny + 1)
    xc = 0.5 * (xe[:-1] + xe[1:])
    yc = 0.5 * (ye[:-1] + ye[1:])
    X, Y = np.meshgrid(xc, yc)
    # Two positive patches + one negative patch.
    pos1 = 4 * np.exp(-((X + 18) ** 2 + (Y - 6) ** 2) / 40)
    pos2 = 3 * np.exp(-((X - 12) ** 2 + (Y - 12) ** 2) / 30)
    neg = -5 * np.exp(-((X - 5) ** 2 + (Y + 10) ** 2) / 50)
    V = pos1 + pos2 + neg + rng.normal(0, 0.4, X.shape)
    # Elliptical mask (molecule silhouette).
    mask = ((X / 30) ** 2 + (Y / 22) ** 2) <= 1.0
    return SurfaceElectrostaticsInput(
        x_edges=xe.tolist(),
        y_edges=ye.tolist(),
        potential=V.tolist(),
        mask=mask.tolist(),
    )


_META = RecipeMetadata(
    name="surface_electrostatics_colormap",
    modality="cryoem_and_structure",
    family=RecipeFamily.heatmap,
    answers_question=(
        "What is the electrostatic potential on the molecular "
        "surface, and where are the positive / negative patches?"
    ),
    required_fields=("x_edges", "y_edges", "potential"),
    optional_fields=("mask", "title"),
    file_format_hints=("npz",),
    alternatives_in_modality=("local_resolution_surface",),
)


@register_recipe(
    metadata=_META,
    contract=SurfaceElectrostaticsInput,
    demo_contract=_demo,
)
def render(contract: SurfaceElectrostaticsInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 4.0))
    AESTHETIC.apply_to_ax(ax)

    xe = np.asarray(contract.x_edges, float)
    ye = np.asarray(contract.y_edges, float)
    V = np.asarray(contract.potential, float)

    if contract.mask is not None:
        mask = np.asarray(contract.mask, bool)
        V_plot = np.ma.array(V, mask=~mask)
    else:
        V_plot = V

    v_abs = float(max(abs(V).max(), 1e-6))
    # Common electrostatic convention: -5..+5 kT/e.
    v_abs = max(v_abs, 5.0)

    im = ax.pcolormesh(xe, ye, V_plot,
                       cmap="RdBu_r", vmin=-v_abs, vmax=v_abs,
                       shading="auto", zorder=2)

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.040, pad=0.03)
    cbar.set_label("electrostatic potential (kT/e)", fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    # Contour at ±1 kT/e.
    xc = 0.5 * (xe[:-1] + xe[1:])
    yc = 0.5 * (ye[:-1] + ye[1:])
    Xc, Yc = np.meshgrid(xc, yc)
    ax.contour(Xc, Yc, V, levels=[-1.0, 1.0],
               colors=["#1565C0", "#C62828"],
               linewidths=[0.8, 0.8], linestyles=["-", "-"],
               zorder=4)

    ax.set_xlabel("x (Å)")
    ax.set_ylabel("y (Å)")
    ax.set_aspect("equal")

    # Charge-patch summary.
    valid = V_plot if isinstance(V_plot, np.ndarray) else V
    valid_arr = (V[~V_plot.mask] if hasattr(V_plot, "mask")
                 else valid.ravel())
    pos_frac = float(np.mean(valid_arr > 1.0))
    neg_frac = float(np.mean(valid_arr < -1.0))
    ax.set_title(
        f"{contract.title}  ·  +/- patch frac "
        f"{smart_fmt(pos_frac)} / {smart_fmt(neg_frac)}",
        fontsize=8.4, pad=4,
    )

    ax.text(0.02, 0.97,
            f"max +V = {smart_fmt(float(V.max()))} kT/e\n"
            f"min -V = {smart_fmt(float(V.min()))} kT/e",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.4, color="#FFFFFF",
            bbox=dict(boxstyle="round,pad=0.22", fc="#222222",
                      ec="none", alpha=0.7),
            zorder=6)
    return ax
