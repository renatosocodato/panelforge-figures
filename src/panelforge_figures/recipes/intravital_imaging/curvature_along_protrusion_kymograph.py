"""Curvature along protrusion kymograph — kappa(s, t) heatmap with
ridge-tracked max-curvature line overlay.

Heatmap family: >=1 imshow / pcolormesh.
"""

from __future__ import annotations

import numpy as np

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC
from ._shared import ProtrusionPolylineWithTime


class CurvatureKymographInput(RecipeContract):
    polyline: ProtrusionPolylineWithTime
    normalize_arclength: bool = True
    cmap: str = "magma"
    title: str = "Curvature kymograph kappa(s, t)"


def _demo() -> CurvatureKymographInput:
    rng = np.random.default_rng(3131)
    n_t = 30
    n_s = 40
    t = np.arange(n_t).astype(float)
    # Build a synthetic kappa(s, t) where the ridge migrates along s.
    curvature = np.zeros((n_t, n_s))
    for ti in range(n_t):
        ridge_s = 5 + 0.7 * ti  # ridge moves rightward
        curvature[ti] = 0.3 * np.exp(
            -((np.arange(n_s) - ridge_s) / 4.0) ** 2
        ) + rng.normal(0, 0.02, n_s)
    # Generate dummy polyline geometry.
    polyline = []
    for ti in range(n_t):
        xs = np.linspace(0, 10, n_s)
        ys = 0.5 * np.sin(np.linspace(0, np.pi, n_s)) * (1 + 0.05 * ti)
        polyline.append([[float(x), float(y)] for x, y in zip(xs, ys)])
    return CurvatureKymographInput(
        polyline=ProtrusionPolylineWithTime(
            protrusion_id="P00",
            parent_cell_id="C00",
            t_s=t.tolist(),
            polyline_xy_um_per_t=polyline,
            curvature_per_s_per_t=curvature.tolist(),
        ),
    )


_META = RecipeMetadata(
    name="curvature_along_protrusion_kymograph",
    modality="intravital_imaging",
    family=RecipeFamily.heatmap,
    answers_question=(
        "How does the curvature kappa(s, t) along a single protrusion "
        "evolve over time?"
    ),
    required_fields=("polyline",),
    optional_fields=("normalize_arclength", "cmap", "title"),
    file_format_hints=("yaml",),
    alternatives_in_modality=("vessel_diameter_kymograph",),
)


@register_recipe(
    metadata=_META,
    contract=CurvatureKymographInput,
    demo_contract=_demo,
)
def render(contract: CurvatureKymographInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.8, 3.8))
    AESTHETIC.apply_to_ax(ax)

    poly = contract.polyline
    if poly.curvature_per_s_per_t is None:
        ax.text(0.5, 0.5, "no curvature data",
                transform=ax.transAxes, ha="center", va="center",
                fontsize=7.2, color="#888888")
        ax.set_title(contract.title, fontsize=8.4, pad=4)
        return ax

    curvature = np.asarray(poly.curvature_per_s_per_t, float)
    t = np.asarray(poly.t_s, float)
    n_t, n_s = curvature.shape
    if contract.normalize_arclength:
        s = np.linspace(0, 1, n_s)
        ax.set_ylabel("normalized arc length s / L")
    else:
        s = np.arange(n_s).astype(float)
        ax.set_ylabel("arc length s (um)")

    mesh = ax.pcolormesh(t, s, curvature.T, cmap=contract.cmap,
                         shading="auto", zorder=2)
    cbar = ax.figure.colorbar(mesh, ax=ax, fraction=0.04, pad=0.03)
    cbar.set_label("kappa (1/um)", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.0)

    # Ridge-tracked max-kappa line per timepoint.
    ridge_s = s[curvature.argmax(axis=1)]
    ax.plot(t, ridge_s, color="#FFFFFF", lw=1.4, zorder=5,
            label="max-kappa ridge")

    ax.set_xlabel("time t (s)")
    ax.legend(fontsize=6.8, frameon=True, framealpha=0.85,
              edgecolor="#BBBBBB", facecolor="white",
              loc="lower right", handlelength=1.4)

    max_k = float(curvature.max())
    mean_k = float(curvature.mean())
    ax.set_title(
        f"{contract.title}  ·  max kappa = {smart_fmt(max_k)}  ·  "
        f"mean = {smart_fmt(mean_k)}",
        fontsize=8.2, pad=4,
    )
    return ax
