"""Force-budget schematic with data — methods-style schematic of the
protrusion force budget (drag, elastic, active, dissipation) with
measured per-term values + 95% CI overlaid as horizontal bars on
the right side of the figure; sign convention coloured.

Conceptual family — pure matplotlib annotation; no strict family
quality rule.
"""

from __future__ import annotations

import matplotlib.patches as mpatches
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
from ._shared import ForceBudgetTerm

_SIGN_COLOR = {
    "+": "#2E7D32",   # green for forward / pushing
    "-": "#C62828",   # red for opposing / restoring
}


class ForceBudgetInput(RecipeContract):
    terms: list[ForceBudgetTerm] = Field(..., min_length=2)
    title: str = "Force budget schematic with data"


def _demo() -> ForceBudgetInput:
    rng = np.random.default_rng(706)
    terms = [
        ForceBudgetTerm(
            term="active stress (actomyosin)",
            value_pN=4.2, ci_lo=3.6, ci_hi=4.8, sign="+",
        ),
        ForceBudgetTerm(
            term="elastic restoring (Lp)",
            value_pN=-2.4, ci_lo=-2.9, ci_hi=-1.9, sign="-",
        ),
        ForceBudgetTerm(
            term="viscous drag (cortex)",
            value_pN=-1.5, ci_lo=-1.9, ci_hi=-1.1, sign="-",
        ),
        ForceBudgetTerm(
            term="confinement penalty",
            value_pN=-0.4, ci_lo=-0.7, ci_hi=-0.1, sign="-",
        ),
    ]
    # add a tiny perturbation for realism
    _ = rng.normal(0, 0.05, len(terms))
    return ForceBudgetInput(terms=terms)


_META = RecipeMetadata(
    name="force_budget_schematic_with_data",
    modality="biophysics_scaling",
    family=RecipeFamily.conceptual,
    answers_question=(
        "Across the protrusion force budget (active, elastic, drag, "
        "confinement), what are the measured per-term magnitudes "
        "and signs?"
    ),
    required_fields=("terms",),
    optional_fields=("title",),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("force_length_characteristic",),
)


@register_recipe(
    metadata=_META,
    contract=ForceBudgetInput,
    demo_contract=_demo,
)
def render(contract: ForceBudgetInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 4.0))
    AESTHETIC.apply_to_ax(ax)

    n = len(contract.terms)
    ax.set_xlim(0, 1)
    ax.set_ylim(n - 0.3, -0.7)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])

    # Left half: schematic boxes labelled with each term.  Right half:
    # CI bars with measured values.
    schematic_x = 0.05
    schematic_w = 0.36
    bar_x_lo = 0.45
    bar_x_hi = 0.95

    # Pre-compute global bar range.
    all_lo = [t.ci_lo if t.ci_lo is not None else t.value_pN
              for t in contract.terms]
    all_hi = [t.ci_hi if t.ci_hi is not None else t.value_pN
             for t in contract.terms]
    v_max = max(abs(min(all_lo)), abs(max(all_hi)))
    v_max = max(v_max, 1.0)

    # Bar-axis baseline (zero line) inside the right half.
    bar_zero_x = bar_x_lo + (bar_x_hi - bar_x_lo) * 0.5

    def _bar_x_of(value: float) -> float:
        return bar_zero_x + (value / v_max) * (bar_x_hi - bar_x_lo) * 0.45

    # Zero reference line.
    ax.plot([bar_zero_x, bar_zero_x], [-0.30, n - 0.5],
            color="#888888", lw=0.7, ls="--", zorder=2)
    ax.text(bar_zero_x, -0.55, "0 pN", ha="center", va="top",
            fontsize=6.4, color="#666666", style="italic")

    # Headers.
    ax.text((schematic_x + schematic_w / 2), -0.78,
            "force budget term", ha="center", va="bottom",
            fontsize=7.6, color="#222222", fontweight="bold")
    ax.text((bar_x_lo + bar_x_hi) / 2, -0.78,
            "measured value (pN)  ±  95% CI",
            ha="center", va="bottom", fontsize=7.6,
            color="#222222", fontweight="bold")

    for i, term in enumerate(contract.terms):
        cy = float(i)
        # Schematic box (left).
        colour = _SIGN_COLOR.get(term.sign, "#888888")
        box = mpatches.FancyBboxPatch(
            (schematic_x, cy - 0.30),
            schematic_w, 0.60,
            boxstyle="round,pad=0.02",
            facecolor=colour, edgecolor="white",
            linewidth=0.6, alpha=0.85, zorder=3,
        )
        ax.add_patch(box)
        ax.text(schematic_x + schematic_w / 2, cy, term.term,
                ha="center", va="center", fontsize=6.6,
                color="white", fontweight="bold", zorder=4)

        # Connecting arrow to bar.
        arrow = mpatches.FancyArrowPatch(
            (schematic_x + schematic_w + 0.005, cy),
            (bar_x_lo - 0.005, cy),
            arrowstyle="->", mutation_scale=10,
            color="#999999", linewidth=0.9, zorder=2,
        )
        ax.add_patch(arrow)

        # Right half: CI bar + central marker.
        x_lo = _bar_x_of(term.ci_lo if term.ci_lo is not None
                         else term.value_pN)
        x_hi = _bar_x_of(term.ci_hi if term.ci_hi is not None
                         else term.value_pN)
        x_pt = _bar_x_of(term.value_pN)
        ax.plot([x_lo, x_hi], [cy, cy],
                color=colour, lw=2.2, alpha=0.85, zorder=4)
        ax.scatter([x_pt], [cy], s=44, marker="o",
                   facecolor=colour, edgecolor="white",
                   linewidth=0.7, zorder=5)
        # Numeric value annotation.
        ci_str = (f" [{smart_fmt(term.ci_lo)}, {smart_fmt(term.ci_hi)}]"
                  if term.ci_lo is not None and term.ci_hi is not None
                  else "")
        ax.text(bar_x_hi + 0.005, cy,
                f"{smart_fmt(term.value_pN)} pN{ci_str}",
                ha="left", va="center", fontsize=6.0,
                color="#222222", zorder=5)

    # Compute net force.
    net = sum(t.value_pN for t in contract.terms)
    ax.set_title(
        f"{contract.title}  ·  net = {smart_fmt(net)} pN  "
        f"({n} terms)",
        fontsize=8.4, pad=8,
    )
    return ax
