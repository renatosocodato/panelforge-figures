"""Fractal-dimension scaling — N(L) ~ L^D_f box-counting diagnostic.

Distinct from `log_log_scaling_with_slope_box` (generic power-law
fit): here the fitted exponent has a specific semantic (the fractal
dimension D_f) and the panel adds a scale-window inset showing D_f(L)
across the log range to reveal crossover scales.
"""

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


class FractalDimensionInput(RecipeContract):
    box_size: list[float] = Field(..., min_length=5)
    box_count: list[float] = Field(..., min_length=5)
    theory_D: float | None = Field(
        None, description="expected fractal dimension for reference"
    )
    x_label: str = "box size L"
    y_label: str = "N(L)"
    title: str = "Box-counting fractal dimension"


def _demo() -> FractalDimensionInput:
    rng = np.random.default_rng(311)
    L = np.logspace(-2, 1.5, 24)
    # True D_f = 1.58 (Koch-ish), noisy.
    N = (L / L.min()) ** (-1.58) * np.exp(rng.normal(0, 0.06, L.size))
    return FractalDimensionInput(
        box_size=L.tolist(),
        box_count=N.tolist(),
        theory_D=1.58,
        x_label="box size L (μm)",
        y_label="N(L)",
        title="Neurite fractal dimension",
    )


_META = RecipeMetadata(
    name="fractal_dimension_scaling",
    modality="biophysics_scaling",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "What is the box-counting fractal dimension D_f of a structure "
        "across scales?"
    ),
    required_fields=("box_size", "box_count"),
    optional_fields=("theory_D", "x_label", "y_label", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("log_log_scaling_with_slope_box",),
)


@register_recipe(
    metadata=_META,
    contract=FractalDimensionInput,
    demo_contract=_demo,
)
def render(contract: FractalDimensionInput, ax=None, **_):
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.6))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)
    accent = palette[2]

    L = np.asarray(contract.box_size, float)
    N = np.asarray(contract.box_count, float)
    lL, lN = np.log10(L), np.log10(N)
    slope, intercept = np.polyfit(lL, lN, 1)
    D_f = -slope   # N ~ L^-D_f convention

    ax.scatter(L, N, s=26, color=accent, alpha=0.8,
               edgecolor="white", linewidth=0.5, zorder=3,
               label="data")

    xfit = np.logspace(lL.min(), lL.max(), 100)
    yfit = 10 ** (slope * np.log10(xfit) + intercept)
    ax.plot(xfit, yfit, color="#222222", lw=1.1, zorder=4,
            label=f"fit (D$_f$ = {smart_fmt(float(D_f))})")

    if contract.theory_D is not None:
        y_th = 10 ** (-contract.theory_D * np.log10(xfit) + intercept)
        ax.plot(xfit, y_th, color="#888888", lw=0.8, ls="--", zorder=3,
                label=f"theory (D$_f$ = {smart_fmt(float(contract.theory_D))})")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(contract.x_label)
    ax.set_ylabel(contract.y_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="lower left",
              handlelength=1.6)
    ax.grid(axis="both", which="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Local D_f(L) window inset — slide a 5-point window across log L.
    win = max(5, len(L) // 5)
    centers = []
    D_locs = []
    for i in range(len(L) - win + 1):
        s_local, _ = np.polyfit(lL[i:i + win], lN[i:i + win], 1)
        centers.append(10 ** np.mean(lL[i:i + win]))
        D_locs.append(-s_local)

    inset = inset_axes(ax, width="34%", height="30%",
                       loc="upper right", borderpad=0.8)
    AESTHETIC.apply_to_ax(inset)
    inset.axhline(D_f, color="#222222", lw=0.8, zorder=2)
    inset.scatter(centers, D_locs, s=12, color=accent, alpha=0.8,
                  edgecolor="white", linewidth=0.4, zorder=3)
    inset.plot(centers, D_locs, color=accent, lw=0.8, alpha=0.5, zorder=3)
    inset.set_xscale("log")
    inset.set_xlabel("L", fontsize=6.2)
    inset.set_ylabel(r"local D$_f$", fontsize=6.2)
    inset.tick_params(labelsize=6.2)
    inset.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    inset.set_axisbelow(True)

    ax.text(0.02, 0.04,
            f"D$_f$ = {smart_fmt(float(D_f))}  (window σ = "
            f"{smart_fmt(float(np.std(D_locs)))})",
            transform=ax.transAxes, ha="left", va="bottom",
            fontsize=6.8, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=5)
    return ax
