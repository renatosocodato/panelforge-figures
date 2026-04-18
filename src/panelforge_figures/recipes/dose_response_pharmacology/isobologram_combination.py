"""Isobologram — combination pharmacology showing synergy / additivity / antagonism."""

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


class IsoboleInput(RecipeContract):
    ic50_A: float
    ic50_B: float
    mixtures: list[tuple[float, float]] = Field(
        ..., description="each entry is (dose_A, dose_B) at a fixed effect level"
    )
    drug_a_name: str = "Drug A"
    drug_b_name: str = "Drug B"
    effect_level: float = 0.5
    title: str = "Isobologram"


def _demo() -> IsoboleInput:
    ic50_A = 100.0                  # nM
    ic50_B = 250.0                  # nM
    # Synergistic combos below the additive line + a few antagonistic above.
    mix = [
        (20, 60),    # synergy
        (40, 75),    # synergy
        (60, 100),   # synergy
        (80, 150),   # near additive
        (10, 230),   # synergy strong
        (95, 200),   # weak antagonism
        (120, 300),  # antagonism
    ]
    return IsoboleInput(
        ic50_A=ic50_A, ic50_B=ic50_B, mixtures=mix,
        drug_a_name="AntagonistA",
        drug_b_name="ReceptorB inhibitor",
        effect_level=0.5,
    )


_META = RecipeMetadata(
    name="isobologram_combination",
    modality="dose_response_pharmacology",
    family=RecipeFamily.scatter_collapse,
    answers_question="At a fixed effect level, do drug pairs combine additively, synergistically, or antagonistically?",
    required_fields=("ic50_A", "ic50_B", "mixtures"),
    optional_fields=("drug_a_name", "drug_b_name", "effect_level", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("drug_combo_heatmap",),
)


@register_recipe(metadata=_META, contract=IsoboleInput, demo_contract=_demo)
def render(contract: IsoboleInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.4, 3.4))
    AESTHETIC.apply_to_ax(ax)

    a50 = contract.ic50_A
    b50 = contract.ic50_B

    # Additive (Loewe) line.
    ax.plot([a50, 0], [0, b50], color="#333333", lw=1.0, ls="--", zorder=2)
    # Axis markers at IC50s.
    ax.scatter([a50, 0], [0, b50], s=28, color="#333333",
               zorder=3)

    # Shade synergy and antagonism regions.
    xs = np.linspace(0, a50, 60)
    ys_add = b50 * (1 - xs / a50)
    ax.fill_between(xs, 0, ys_add, color="#A5D6A7", alpha=0.18, zorder=1,
                    label="synergy region")
    ax.fill_between(xs, ys_add, b50 * 1.5,
                    color="#EF9A9A", alpha=0.15, zorder=1,
                    label="antagonism region")

    # Plot mixture points — classify by combination index CI = d_A/IC50_A + d_B/IC50_B.
    syn_color = "#2E7D32"
    ant_color = "#C62828"
    add_color = "#555555"
    for d_a, d_b in contract.mixtures:
        ci = d_a / a50 + d_b / b50
        if ci < 0.9:
            color = syn_color
        elif ci > 1.1:
            color = ant_color
        else:
            color = add_color
        ax.scatter([d_a], [d_b], s=46, color=color,
                   edgecolor="white", linewidth=0.8, zorder=4)

    ax.set_xlim(0, a50 * 1.4)
    ax.set_ylim(0, b50 * 1.5)
    ax.set_xlabel(f"{contract.drug_a_name} (nM)")
    ax.set_ylabel(f"{contract.drug_b_name} (nM)")
    ax.set_title(
        f"{contract.title} at effect = {int(contract.effect_level*100)}%",
        fontsize=9.0, pad=4,
    )
    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              handlelength=1.6)

    ax.text(0.02, 0.04,
            r"IC$_{50}^\mathrm{A}$ = " + smart_fmt(a50) + " nM\n"
            r"IC$_{50}^\mathrm{B}$ = " + smart_fmt(b50) + " nM",
            transform=ax.transAxes, ha="left", va="bottom",
            fontsize=6.6, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=5)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
