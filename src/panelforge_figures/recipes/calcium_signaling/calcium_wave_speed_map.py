"""Spatial map of local Ca2+ wave speed (μm/s).

Pixel-wise wave speed derived from the arrival-time field t(x, y) as
speed = 1 / |∇t|. Distinct from `calcium_propagation_wavefront`, which
shows the arrival-time field with iso-contours.
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


class WaveSpeedMapInput(RecipeContract):
    x_um: list[float] = Field(..., min_length=3)
    y_um: list[float] = Field(..., min_length=3)
    speed_field_um_per_s: list[list[float]] = Field(
        ..., description="speed[j][i] at (x_um[i], y_um[j]); NaN where no wave"
    )
    initiation_point_um: tuple[float, float] | None = None
    title: str = "Calcium-wave speed map"


def _demo() -> WaveSpeedMapInput:
    rng = np.random.default_rng(311)
    x = np.linspace(0, 120, 60)
    y = np.linspace(0, 100, 50)
    X, Y = np.meshgrid(x, y)
    cx, cy = 40.0, 50.0
    r = np.hypot(X - cx, Y - cy)
    # Speed decays with r (wave slowing), plus some heterogeneity.
    speed = 22.0 * np.exp(-r / 60.0) * (1 + rng.normal(0, 0.12, X.shape))
    speed[r > 60] = np.nan
    speed = np.clip(speed, 0, None)
    return WaveSpeedMapInput(
        x_um=x.tolist(),
        y_um=y.tolist(),
        speed_field_um_per_s=speed.tolist(),
        initiation_point_um=(cx, cy),
    )


_META = RecipeMetadata(
    name="calcium_wave_speed_map",
    modality="calcium_signaling",
    family=RecipeFamily.heatmap,
    answers_question=(
        "Across the field, what is the local wave-propagation speed "
        "(μm/s)?"
    ),
    required_fields=("x_um", "y_um", "speed_field_um_per_s"),
    optional_fields=("initiation_point_um", "title"),
    file_format_hints=("npz", "tif"),
    alternatives_in_modality=("calcium_propagation_wavefront",),
)


@register_recipe(
    metadata=_META,
    contract=WaveSpeedMapInput,
    demo_contract=_demo,
)
def render(contract: WaveSpeedMapInput, ax=None, **_):
    import matplotlib as mpl

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.6))
    AESTHETIC.apply_to_ax(ax)

    S = np.asarray(contract.speed_field_um_per_s, float)
    x = np.asarray(contract.x_um, float)
    y = np.asarray(contract.y_um, float)

    cmap = mpl.colormaps["magma"]
    vmax = float(np.nanmax(S))
    im = ax.imshow(
        S, origin="lower", cmap=cmap,
        extent=(x[0], x[-1], y[0], y[-1]),
        vmin=0.0, vmax=max(vmax, 1e-9),
        aspect="equal", interpolation="nearest",
    )

    if contract.initiation_point_um is not None:
        ix, iy = contract.initiation_point_um
        ax.scatter([ix], [iy], s=80, marker="*", color="#D32F2F",
                   edgecolor="white", linewidth=1.0, zorder=6)

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("speed (μm/s)", fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    # Mean / peak callout.
    mean_s = float(np.nanmean(S))
    peak_s = float(np.nanmax(S))
    ax.text(0.02, 0.98,
            f"peak = {smart_fmt(peak_s)} μm/s\n"
            f"mean = {smart_fmt(mean_s)} μm/s",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.4, color="white",
            bbox=dict(boxstyle="round,pad=0.20", fc="#333333",
                      ec="none", alpha=0.70),
            zorder=7)

    # Scale bar (20 μm).
    sb_x = x[0] + 0.05 * (x[-1] - x[0])
    sb_y = y[0] + 0.05 * (y[-1] - y[0])
    ax.plot([sb_x, sb_x + 20], [sb_y, sb_y],
            color="white", lw=2.2, solid_capstyle="butt", zorder=7)
    ax.text(sb_x + 10, sb_y + 1.5, "20 μm",
            ha="center", va="bottom", fontsize=6.2, color="white",
            bbox=dict(boxstyle="round,pad=0.14", fc="#333333",
                      ec="none", alpha=0.65), zorder=7)

    ax.set_xlabel("x (μm)")
    ax.set_ylabel("y (μm)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    return ax
