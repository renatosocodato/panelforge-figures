"""1-D energy-landscape cartoon — schematic U(x) with labelled wells,
barriers, and a k_B T scale bar.

Conceptual family: ≥3 text artists + ≥2 patches. Built with annotation
arrows between wells (no data).
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


class EnergyLandscapeInput(RecipeContract):
    well_positions: list[float] = Field(..., min_length=2)
    well_depths: list[float] = Field(..., description="depth below U=0, positive values")
    well_labels: list[str] = Field(..., min_length=2)
    barrier_positions: list[float] = Field(...)
    barrier_heights: list[float] = Field(..., description="barrier heights in units of kT")
    kT: float = Field(1.0, description="k_B T in the plotted energy unit")
    title: str = "1-D energy landscape"


def _demo() -> EnergyLandscapeInput:
    return EnergyLandscapeInput(
        well_positions=[1.0, 3.5, 6.2],
        well_depths=[4.0, 5.5, 3.2],
        well_labels=["homeostatic", "surveillant", "activated"],
        barrier_positions=[2.2, 4.8],
        barrier_heights=[6.0, 4.2],
        kT=1.0,
        title="Microglial-state landscape (cartoon)",
    )


_META = RecipeMetadata(
    name="energy_landscape_1d_cartoon",
    modality="biophysics_scaling",
    family=RecipeFamily.conceptual,
    answers_question=(
        "How does a 1-D energy landscape U(x) explain the state "
        "lifetimes and transitions of a system?"
    ),
    required_fields=(
        "well_positions", "well_depths", "well_labels",
        "barrier_positions", "barrier_heights",
    ),
    optional_fields=("kT", "title"),
    file_format_hints=("json",),
    alternatives_in_modality=("force_length_characteristic",),
)


@register_recipe(
    metadata=_META,
    contract=EnergyLandscapeInput,
    demo_contract=_demo,
)
def render(contract: EnergyLandscapeInput, ax=None, **_):
    import matplotlib.patches as mpatches

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.8))
    AESTHETIC.apply_to_ax(ax)

    wells_x = np.asarray(contract.well_positions, float)
    wells_d = np.asarray(contract.well_depths, float)
    labels = contract.well_labels
    bars_x = np.asarray(contract.barrier_positions, float)
    bars_h = np.asarray(contract.barrier_heights, float)

    # Build a smooth U(x) from sum of quadratic wells and gaussian barriers.
    x_lo = min(wells_x.min(), bars_x.min()) - 1.0
    x_hi = max(wells_x.max(), bars_x.max()) + 1.0
    x = np.linspace(x_lo, x_hi, 500)
    U = np.zeros_like(x)
    for xw, d in zip(wells_x, wells_d):
        U += -d * np.exp(-((x - xw) / 0.7) ** 2)
    for xb, h in zip(bars_x, bars_h):
        U += h * np.exp(-((x - xb) / 0.4) ** 2)

    # Baseline stroke of the landscape.
    ax.plot(x, U, color="#222222", lw=1.3, zorder=4)
    # Fill below curve.
    ax.fill_between(x, U, U.max() + 1, color="#F4F4F4",
                    edgecolor="none", zorder=2)

    # Wells as oval patches at their floor.
    for xw, d, nm in zip(wells_x, wells_d, labels):
        y_floor = -d
        ax.add_patch(mpatches.Ellipse(
            (xw, y_floor), 0.5, 0.35,
            facecolor="#1565C0", edgecolor="white", linewidth=0.7,
            alpha=0.85, zorder=6,
        ))
        ax.text(xw, y_floor - 0.8, nm,
                ha="center", va="top", fontsize=7.0,
                color="#1565C0", zorder=7)

    # Barriers as ticks.
    for xb, h in zip(bars_x, bars_h):
        # Compute U at barrier top from the curve.
        y_top = float(np.interp(xb, x, U))
        ax.add_patch(mpatches.FancyBboxPatch(
            (xb - 0.25, y_top - 0.1), 0.5, 0.4,
            boxstyle="round,pad=0.05",
            facecolor="#C62828", edgecolor="white", linewidth=0.6,
            alpha=0.85, zorder=6,
        ))
        ax.text(xb, y_top + 0.65,
                rf"$\Delta U = {smart_fmt(h)}\,k_B T$",
                ha="center", va="bottom", fontsize=6.8,
                color="#C62828", zorder=7)

    # kT scale bar (top-right).
    kT = float(contract.kT)
    x_sb = x_hi - 0.7
    y_sb_lo = U.max() * 0.4
    ax.plot([x_sb, x_sb], [y_sb_lo, y_sb_lo + kT],
            color="#444444", lw=1.3, zorder=7)
    ax.plot([x_sb - 0.1, x_sb + 0.1], [y_sb_lo, y_sb_lo],
            color="#444444", lw=0.8, zorder=7)
    ax.plot([x_sb - 0.1, x_sb + 0.1], [y_sb_lo + kT, y_sb_lo + kT],
            color="#444444", lw=0.8, zorder=7)
    ax.text(x_sb - 0.22, y_sb_lo + kT / 2, r"$k_B T$",
            ha="right", va="center", fontsize=7.0, color="#444444",
            zorder=7)

    # Arrows between wells: show forward and reverse rates symbolically.
    for i in range(len(wells_x) - 1):
        x_a = wells_x[i]
        x_b = wells_x[i + 1]
        y_a = -wells_d[i]
        y_b = -wells_d[i + 1]
        ax.annotate("", xy=(x_b - 0.25, y_b), xytext=(x_a + 0.25, y_a),
                    arrowprops=dict(arrowstyle="->", color="#555555",
                                    lw=0.8, alpha=0.7),
                    zorder=5)

    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(U.min() - 1.5, U.max() + 1.5)
    ax.set_xlabel("reaction coordinate x")
    ax.set_ylabel(r"U(x) / $k_B T$")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.set_yticks([])
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    return ax
