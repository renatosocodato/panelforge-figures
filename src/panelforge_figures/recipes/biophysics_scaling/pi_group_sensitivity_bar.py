"""Π-group sensitivity bar — horizontal bars ranking each Buckingham-Π
group by its contribution to the response-variable variance.

Ladder family: ≥3 bars, one labelled numeric.
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


class PiGroupInput(RecipeContract):
    group_names: list[str] = Field(..., min_length=3)
    contribution: list[float] = Field(..., description="variance share in [0,1]")
    group_expr: list[str] | None = Field(
        None, description="optional formal expression per group, e.g. 'v L / ν'"
    )
    title: str = "Π-group variance contributions"


def _demo() -> PiGroupInput:
    rng = np.random.default_rng(811)
    names = ["Π1: v L / ν", "Π2: ρ v² / E", "Π3: L / λ",
             "Π4: τ_ext / τ_int", "Π5: k_B T / U_0"]
    raw = rng.dirichlet(np.array([4, 2, 3, 1.5, 0.8]))
    return PiGroupInput(
        group_names=[n.split(":")[0].strip() for n in names],
        contribution=raw.tolist(),
        group_expr=[n.split(":")[1].strip() for n in names],
        title="Force-balance Π-group decomposition",
    )


_META = RecipeMetadata(
    name="pi_group_sensitivity_bar",
    modality="biophysics_scaling",
    family=RecipeFamily.ladder,
    answers_question=(
        "Which Buckingham-Π group contributes most to the response "
        "variable's variance?"
    ),
    required_fields=("group_names", "contribution"),
    optional_fields=("group_expr", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("scaling_exponent_ci_forest",),
)


@register_recipe(
    metadata=_META,
    contract=PiGroupInput,
    demo_contract=_demo,
)
def render(contract: PiGroupInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.6))
    AESTHETIC.apply_to_ax(ax)

    names = contract.group_names
    contrib = np.asarray(contract.contribution, float)
    exprs = (contract.group_expr
             if contract.group_expr is not None
             else [""] * len(names))

    # Sort by contribution descending.
    order = np.argsort(-contrib)
    names_s = [names[i] for i in order]
    contrib_s = contrib[order]
    exprs_s = [exprs[i] for i in order]

    y = np.arange(len(names_s))
    # Colour gradient by rank.
    colors = ["#1565C0", "#1976D2", "#1E88E5", "#42A5F5",
              "#64B5F6", "#90CAF9", "#BBDEFB"]

    bar_colors = [colors[i % len(colors)] for i in range(len(y))]

    ax.barh(y, contrib_s,
            color=bar_colors, edgecolor="white", linewidth=0.7,
            alpha=0.9, zorder=3)

    # Per-bar numeric + formal expression.
    for yi, c, expr in zip(y, contrib_s, exprs_s):
        ax.text(c + 0.01, yi,
                f"{smart_fmt(float(c))}"
                + (f"   ({expr})" if expr else ""),
                va="center", ha="left", fontsize=6.8, color="#333333",
                zorder=5)

    ax.set_yticks(y)
    ax.set_yticklabels(names_s, fontsize=7.0)
    ax.invert_yaxis()
    ax.set_xlabel("variance contribution")
    ax.set_xlim(0, float(contrib_s.max()) * 1.35)
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    # Cumulative top-2 share callout.
    top2 = float(contrib_s[:2].sum())
    ax.text(0.98, 0.04,
            f"top-2 share: {smart_fmt(top2)}   "
            f"top-3 share: {smart_fmt(float(contrib_s[:3].sum()))}",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6.4, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)

    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    return ax
