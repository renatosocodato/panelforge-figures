"""Calcium wave propagation — radial wavefront arrival time map."""

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


class WavefrontInput(RecipeContract):
    x_um: list[float]
    y_um: list[float]
    arrival_time_s: list[list[float]] = Field(
        ..., description="arrival[j][i] at (x[i], y[j]); NaN where no arrival"
    )
    initiation_point_um: tuple[float, float] = (50.0, 50.0)
    title: str = "Calcium wavefront"


def _demo() -> WavefrontInput:
    rng = np.random.default_rng(233)
    x = np.linspace(0, 120, 60)
    y = np.linspace(0, 100, 50)
    X, Y = np.meshgrid(x, y)
    # Radial arrival from origin, 15 μm/s, plus heterogeneity.
    cx, cy = 40, 50
    r = np.hypot(X - cx, Y - cy)
    t_arrival = r / 15.0 * (1 + rng.normal(0, 0.08, X.shape))
    # Beyond ~50 μm, wave dies.
    t_arrival[r > 60] = np.nan
    return WavefrontInput(
        x_um=x.tolist(),
        y_um=y.tolist(),
        arrival_time_s=t_arrival.tolist(),
        initiation_point_um=(cx, cy),
    )


_META = RecipeMetadata(
    name="calcium_propagation_wavefront",
    modality="calcium_signaling",
    family=RecipeFamily.heatmap,
    answers_question="From an initiation point, how does the calcium wavefront propagate through the field, and at what speed?",
    required_fields=("x_um", "y_um", "arrival_time_s"),
    optional_fields=("initiation_point_um", "title"),
    file_format_hints=("npz", "tif"),
    alternatives_in_modality=("event_raster_with_rate",),
)


@register_recipe(metadata=_META, contract=WavefrontInput, demo_contract=_demo)
def render(contract: WavefrontInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.4))
    AESTHETIC.apply_to_ax(ax)

    T = np.array(contract.arrival_time_s, dtype=float)
    X, Y = np.meshgrid(contract.x_um, contract.y_um)

    im = ax.imshow(
        T, origin="lower", cmap=AESTHETIC.continuous_cmap,
        extent=(contract.x_um[0], contract.x_um[-1],
                contract.y_um[0], contract.y_um[-1]),
        aspect="equal", interpolation="nearest",
    )

    # Iso-arrival contours every 1 s.
    if np.isfinite(T).any():
        tmax = np.nanmax(T)
        levels = np.arange(1.0, tmax + 1, 1.0)
        cs = ax.contour(X, Y, T, levels=levels, colors="white",
                        linewidths=0.5, alpha=0.7)
        ax.clabel(cs, inline=True, fontsize=5.6,
                  fmt=lambda v: f"{v:.0f}s", inline_spacing=2)

    # Initiation point star.
    ix, iy = contract.initiation_point_um
    ax.scatter([ix], [iy], s=80, marker="*", color="#D32F2F",
               edgecolor="white", linewidth=1.2, zorder=6)

    # Estimate speed via radial arrival.
    r = np.hypot(X - ix, Y - iy)
    mask = np.isfinite(T)
    if mask.sum() > 10:
        slope, intercept = np.polyfit(T[mask].ravel(), r[mask].ravel(), 1)
        speed = slope
    else:
        speed = 0.0

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("arrival time (s)", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)

    ax.set_xlabel("x (μm)")
    ax.set_ylabel("y (μm)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    ax.text(0.01, 0.99,
            f"init. ({smart_fmt(ix)}, {smart_fmt(iy)}) μm   "
            f"speed ≈ {smart_fmt(speed)} μm/s",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.4, color="white",
            bbox=dict(boxstyle="round,pad=0.18", fc="#333333",
                      ec="none", alpha=0.7),
            zorder=7)
    return ax
