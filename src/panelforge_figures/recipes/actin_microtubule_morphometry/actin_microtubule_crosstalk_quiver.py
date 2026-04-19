"""Actin direction quiver over microtubule density — intra-cell cytoskeletal crosstalk."""

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


class ActinMTCrosstalkInput(RecipeContract):
    x_um: list[float] = Field(...)
    y_um: list[float] = Field(...)
    mt_density: list[list[float]] = Field(
        ..., description="2-D MT density map shape (n_y, n_x)"
    )
    actin_ux: list[list[float]] = Field(
        ..., description="actin x-direction unit-ish component, same grid"
    )
    actin_uy: list[list[float]] = Field(...)
    pixel_size_um: float = 0.2
    title: str = "Actin direction × MT density"


def _demo() -> ActinMTCrosstalkInput:
    rng = np.random.default_rng(817)
    xs = np.linspace(0.0, 40.0, 80)
    ys = np.linspace(0.0, 30.0, 60)
    XX, YY = np.meshgrid(xs, ys)
    # MT density: two foci.
    mt = (np.exp(-((XX - 14) ** 2 + (YY - 16) ** 2) / 60.0)
          + 0.7 * np.exp(-((XX - 28) ** 2 + (YY - 12) ** 2) / 90.0))
    mt = mt + rng.normal(0, 0.03, mt.shape)
    mt = np.clip(mt, 0, None)
    # Actin direction: radial around (14, 16) with some noise.
    dx = XX - 14.0
    dy = YY - 16.0
    mag = np.sqrt(dx * dx + dy * dy) + 1e-6
    ux = dx / mag + rng.normal(0, 0.2, mag.shape)
    uy = dy / mag + rng.normal(0, 0.2, mag.shape)
    norm = np.sqrt(ux * ux + uy * uy) + 1e-6
    ux /= norm
    uy /= norm
    return ActinMTCrosstalkInput(
        x_um=xs.tolist(),
        y_um=ys.tolist(),
        mt_density=mt.tolist(),
        actin_ux=ux.tolist(),
        actin_uy=uy.tolist(),
    )


_META = RecipeMetadata(
    name="actin_microtubule_crosstalk_quiver",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.heatmap,
    answers_question=(
        "Where do actin orientations align with or cross microtubule density "
        "peaks within a cell?"
    ),
    required_fields=("x_um", "y_um", "mt_density", "actin_ux", "actin_uy"),
    optional_fields=("pixel_size_um", "title"),
    file_format_hints=("npz", "tif"),
    alternatives_in_modality=(
        "filament_orientation_histogram",
        "actin_mt_ratio_spatial_map",
    ),
)


@register_recipe(
    metadata=_META,
    contract=ActinMTCrosstalkInput,
    demo_contract=_demo,
)
def render(contract: ActinMTCrosstalkInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.8))
    AESTHETIC.apply_to_ax(ax)

    xs = np.asarray(contract.x_um, float)
    ys = np.asarray(contract.y_um, float)
    XX, YY = np.meshgrid(xs, ys)
    mt = np.asarray(contract.mt_density, float)
    ux = np.asarray(contract.actin_ux, float)
    uy = np.asarray(contract.actin_uy, float)

    # MT density pcolormesh backdrop.
    mesh = ax.pcolormesh(
        XX, YY, mt, cmap=AESTHETIC.continuous_cmap, shading="auto",
        zorder=1, rasterized=True,
    )

    # Subsample for the quiver so arrows are readable at gallery size.
    step = max(4, min(XX.shape[0], XX.shape[1]) // 16)
    Xs = XX[::step, ::step]
    Ys = YY[::step, ::step]
    Us = ux[::step, ::step]
    Vs = uy[::step, ::step]
    ax.quiver(
        Xs, Ys, Us, Vs,
        color="white", scale=22, width=0.003,
        headwidth=3.6, headlength=4.4, headaxislength=3.8,
        zorder=3,
    )

    # Mandatory scale bar.
    sb_x = float(xs.min()) + (xs.max() - xs.min()) * 0.05
    sb_y = float(ys.min()) + (ys.max() - ys.min()) * 0.08
    ax.plot([sb_x, sb_x + 5], [sb_y, sb_y], color="white", lw=3.0,
            solid_capstyle="butt", zorder=6)
    ax.text(sb_x + 2.5, sb_y + (ys.max() - ys.min()) * 0.04,
            r"5 $\mu$m",
            ha="center", va="bottom", fontsize=6.2, color="white",
            bbox=dict(boxstyle="round,pad=0.14", fc="#333333",
                      ec="none", alpha=0.7))

    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    cbar = ax.figure.colorbar(mesh, ax=ax, fraction=0.04, pad=0.04)
    cbar.set_label("MT density (a.u.)", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)

    # Mean alignment = |mean unit vector|.
    R = float(np.sqrt(ux.mean() ** 2 + uy.mean() ** 2))
    ax.set_title(
        f"{contract.title}  ·  |$\\langle$actin direction$\\rangle$| = {smart_fmt(R)}",
        fontsize=8.6, pad=4,
    )
    return ax
