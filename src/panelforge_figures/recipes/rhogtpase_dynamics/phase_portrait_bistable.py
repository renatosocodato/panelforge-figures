"""Bistable phase portrait — two stable wells with a separating saddle."""

from __future__ import annotations

import numpy as np

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    fixed_point_marker,
    get_palette,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class BistablePortraitInput(RecipeContract):
    well_low: float = -1.0
    well_high: float = 1.0
    coupling_lambda: float = 0.40
    condition: str = "baseline"
    title: str = "RhoA bistable landscape"


def _demo() -> BistablePortraitInput:
    return BistablePortraitInput()


_META = RecipeMetadata(
    name="phase_portrait_bistable",
    modality="rhogtpase_dynamics",
    family=RecipeFamily.phase_portrait,
    answers_question="What does the bistable RhoA landscape look like — two wells and a saddle?",
    required_fields=("well_low", "well_high"),
    optional_fields=("coupling_lambda", "condition", "title"),
    file_format_hints=("pickle", "npz"),
    alternatives_in_modality=("phase_portrait_tristable", "phase_portrait_oscillator"),
)


@register_recipe(metadata=_META, contract=BistablePortraitInput, demo_contract=_demo)
def render(contract: BistablePortraitInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.6))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    xg = np.linspace(-1.8, 1.8, 30)
    yg = np.linspace(-1.2, 1.2, 24)
    X, Y = np.meshgrid(xg, yg)

    # U(x) = 0.25*(x^2 - a^2)^2, wells at ±a.
    a = 0.5 * (contract.well_high - contract.well_low)
    Uflat = 0.25 * (xg ** 2 - a ** 2) ** 2
    U2D = np.tile(Uflat, (len(yg), 1))
    ax.pcolormesh(X, Y, U2D, cmap=AESTHETIC.continuous_cmap,
                  shading="auto", alpha=0.55, zorder=1)

    # Coupled dynamics.
    dUdx = np.gradient(Uflat, xg)[None, :] * np.ones_like(X)
    Vx = -dUdx + contract.coupling_lambda * (Y - X)
    Vy = -0.4 * Y
    ax.streamplot(X, Y, Vx, Vy, color="#EEEEEE", density=0.9,
                  linewidth=0.6, arrowsize=0.6, zorder=2)

    # Fixed points.
    fixed_point_marker(ax, contract.well_low, 0, "stable", label="low")
    fixed_point_marker(ax, contract.well_high, 0, "stable", label="high")
    fixed_point_marker(ax, 0.5 * (contract.well_low + contract.well_high), 0,
                       "saddle")

    # Highlight well colors.
    low_c = palette.pick("HOME")
    high_c = palette.pick("TRAP")
    for xc, col in ((contract.well_low, low_c), (contract.well_high, high_c)):
        ax.axvline(xc, color=col, lw=0.6, ls=":", alpha=0.7, zorder=3)

    ax.set_xlabel("RhoA activity")
    ax.set_ylabel("slow driver")
    ax.set_title(f"{contract.title} · {contract.condition}",
                 fontsize=9.0, pad=4)
    ax.set_xlim(xg.min(), xg.max())
    ax.set_ylim(yg.min(), yg.max())

    ax.text(0.99, 0.02,
            f"λ = {contract.coupling_lambda:.2f}",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6.6, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)
    return ax
