"""Bistability hysteresis loop — redox ratio vs H2O2 with forward + reverse paths."""

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


class HysteresisLoopInput(RecipeContract):
    control: list[float] = Field(..., description="control parameter (e.g. [H2O2])")
    forward_ratio: list[float] = Field(...)
    reverse_ratio: list[float] = Field(...)
    control_label: str = r"[H$_2$O$_2$] (μM)"
    ratio_label: str = "redox ratio"
    title: str = "Bistability hysteresis"


def _demo() -> HysteresisLoopInput:
    x = np.linspace(0, 10, 60)
    # Forward: low branch 0.3 → jumps to high branch 1.6 at x=6.
    fwd = np.where(x < 6, 0.3 + 0.04 * x, 1.3 + 0.05 * (x - 6))
    # Reverse: high branch 1.6 → jumps to low at x=3.
    rev = np.where(x > 3, 1.3 + 0.05 * (x - 6), 0.3 + 0.04 * x)
    return HysteresisLoopInput(
        control=x.tolist(),
        forward_ratio=fwd.tolist(),
        reverse_ratio=rev.tolist(),
    )


_META = RecipeMetadata(
    name="bistability_hysteresis_loop",
    modality="redox_imaging",
    family=RecipeFamily.hysteresis_loop,
    answers_question="Is the redox state bistable — does ramping the control up vs down produce a hysteresis loop?",
    required_fields=("control", "forward_ratio", "reverse_ratio"),
    optional_fields=("control_label", "ratio_label", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("single_cell_ratio_distribution",),
)


@register_recipe(metadata=_META, contract=HysteresisLoopInput, demo_contract=_demo)
def render(contract: HysteresisLoopInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    x = np.array(contract.control, dtype=float)
    fwd = np.array(contract.forward_ratio, dtype=float)
    rev = np.array(contract.reverse_ratio, dtype=float)

    red = palette.pick("reduced")
    ox = palette.pick("oxidized")

    ax.plot(x, fwd, color=ox, lw=1.3, label="forward sweep", zorder=3)
    ax.plot(x, rev, color=red, lw=1.3, label="reverse sweep", zorder=3)

    # Direction arrows at mid-sweep.
    i_mid = len(x) // 2
    ax.annotate("",
                xy=(x[i_mid + 2], fwd[i_mid + 2]),
                xytext=(x[i_mid - 2], fwd[i_mid - 2]),
                arrowprops=dict(arrowstyle="->", color=ox, lw=1.0),
                zorder=4)
    ax.annotate("",
                xy=(x[i_mid - 2], rev[i_mid - 2]),
                xytext=(x[i_mid + 2], rev[i_mid + 2]),
                arrowprops=dict(arrowstyle="->", color=red, lw=1.0),
                zorder=4)

    # Ratio-neutral line.
    ax.axhline(1.0, color="#888888", lw=0.5, ls=":", zorder=1)

    ax.set_xlabel(contract.control_label)
    ax.set_ylabel(contract.ratio_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="upper left",
              handlelength=1.8)

    # Measure hysteresis area (approx via trapezoids).
    area = float(np.abs(np.trapezoid(fwd - rev, x)))
    ax.text(0.99, 0.04,
            f"loop area = {smart_fmt(area)}",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6.8, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=5)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
