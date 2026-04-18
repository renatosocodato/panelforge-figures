"""1-D potential landscape — U(x) across conditions with well markers."""

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


class Potential1DInput(RecipeContract):
    x: list[float] = Field(...)
    conditions: dict[str, list[float]] = Field(
        ..., description="condition -> U(x)"
    )
    x_label: str = "RhoA activity"
    y_label: str = "U(x)"
    title: str = "Potential landscapes"


def _demo() -> Potential1DInput:
    x = np.linspace(-2, 2, 200)
    conditions = {
        "basal":   0.18 * (x + 1) ** 2 * x ** 2 * (x - 1) ** 2 - 0.25 * x,
        "ROCKi":   0.18 * (x + 1) ** 2 * (x - 0.6) ** 2 - 0.05 * x,      # bistable
        "SRCi":    0.25 * (x + 0.8) ** 2 + 0.02 * x,                     # mono-stable HOME
    }
    return Potential1DInput(
        x=x.tolist(),
        conditions={k: v.tolist() for k, v in conditions.items()},
    )


_META = RecipeMetadata(
    name="potential_landscape_1d",
    modality="rhogtpase_dynamics",
    family=RecipeFamily.diagnostic_curve,
    answers_question="How does the 1-D potential landscape U(x) change between pharmacological conditions?",
    required_fields=("x", "conditions"),
    optional_fields=("x_label", "y_label", "title"),
    file_format_hints=("csv", "pickle"),
    alternatives_in_modality=("potential_landscape_2d_heatmap",),
)


@register_recipe(metadata=_META, contract=Potential1DInput, demo_contract=_demo)
def render(contract: Potential1DInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    x = np.array(contract.x, dtype=float)
    colors_cycle = [palette.pick("HOME"), palette.pick("GATE"),
                    palette.pick("TRAP")]

    for i, (cond, U) in enumerate(contract.conditions.items()):
        U = np.array(U, dtype=float)
        color = colors_cycle[i % len(colors_cycle)]
        ax.plot(x, U, color=color, lw=1.3, label=cond, zorder=3)
        # Fill below.
        ax.fill_between(x, U, U.max(), color=color, alpha=0.05, zorder=2)
        # Well markers (local minima).
        d1 = np.gradient(U)
        minima = np.where((d1[:-1] < 0) & (d1[1:] >= 0))[0] + 1
        for m in minima:
            ax.scatter([x[m]], [U[m]], s=28, color=color,
                       edgecolor="white", linewidth=0.9, zorder=4)
            ax.text(x[m], U[m] - 0.06 * (U.max() - U.min()),
                    smart_fmt(float(x[m])),
                    ha="center", va="top", fontsize=6.4, color=color)

    ax.set_xlabel(contract.x_label)
    ax.set_ylabel(contract.y_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              handlelength=1.6)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
