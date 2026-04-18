"""Force-length characteristic — passive + active + total curve for a biological spring."""

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


class ForceLengthInput(RecipeContract):
    lengths: list[float] = Field(..., description="normalized length (L/L_opt)")
    passive_force: list[float] = Field(...)
    active_force: list[float] = Field(...)
    total_force: list[float] | None = None
    optimal_length: float = 1.0
    x_label: str = "L / L_opt"
    y_label: str = "normalized force"
    title: str = "Force-length characteristic"


def _demo() -> ForceLengthInput:
    L = np.linspace(0.5, 1.7, 120)
    # Active force peaks near L=1 (optimal overlap).
    active = np.exp(-((L - 1.0) / 0.18) ** 2) * 1.0
    # Passive force grows ~exponentially past L=1.2.
    passive = np.where(L <= 1.0, 0.0, (np.exp(3 * (L - 1.0)) - 1) / 20)
    total = active + passive
    return ForceLengthInput(
        lengths=L.tolist(),
        passive_force=passive.tolist(),
        active_force=active.tolist(),
        total_force=total.tolist(),
    )


_META = RecipeMetadata(
    name="force_length_characteristic",
    modality="biophysics_scaling",
    family=RecipeFamily.diagnostic_curve,
    answers_question="How does contractile force depend on sarcomere / fiber length, split into active and passive components?",
    required_fields=("lengths", "passive_force", "active_force"),
    optional_fields=("total_force", "optimal_length", "x_label", "y_label", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("buckling_critical_force_plot",),
)


@register_recipe(metadata=_META, contract=ForceLengthInput, demo_contract=_demo)
def render(contract: ForceLengthInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    L = np.array(contract.lengths, dtype=float)
    passive = np.array(contract.passive_force, dtype=float)
    active = np.array(contract.active_force, dtype=float)
    total = (
        np.array(contract.total_force, dtype=float)
        if contract.total_force is not None
        else passive + active
    )

    # Optimal length reference.
    ax.axvline(contract.optimal_length, color="#888888", lw=0.7, ls="--", zorder=1)

    ax.plot(L, passive, color=palette[5], lw=1.1, label="passive", zorder=3)
    ax.plot(L, active, color=palette[6], lw=1.1, label="active", zorder=3)
    ax.plot(L, total, color="#111111", lw=1.3, label="total", zorder=4)

    ax.fill_between(L, 0, passive, color=palette[5], alpha=0.12, zorder=2)
    ax.fill_between(L, 0, active, color=palette[6], alpha=0.10, zorder=2)

    # Peak marker.
    i_peak = int(np.argmax(total))
    ax.scatter([L[i_peak]], [total[i_peak]], s=42, color="#D32F2F",
               edgecolor="white", linewidth=0.8, zorder=5, marker="*")
    ax.text(L[i_peak], total[i_peak] * 1.03,
            f"peak = {smart_fmt(float(total[i_peak]))}",
            ha="center", va="bottom", fontsize=6.6, color="#D32F2F",
            bbox=dict(boxstyle="round,pad=0.16", fc="white",
                      ec="none", alpha=0.92),
            zorder=6)

    ax.set_xlabel(contract.x_label)
    ax.set_ylabel(contract.y_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="upper left",
              handlelength=1.6)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.set_ylim(0, max(total.max() * 1.15, 0.1))
    return ax
