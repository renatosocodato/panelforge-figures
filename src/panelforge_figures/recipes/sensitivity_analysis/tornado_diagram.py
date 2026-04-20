"""Classic one-at-a-time (OAT) tornado diagram.

For each parameter, sweep it to its lower and upper bound (all others
at nominal) and record the resulting output. Bars extend from the
baseline output to the ±Δ endpoint, split into high-side and low-side
halves and coloured accordingly. Sorted by total width.

Distinct from `sobol_first_total_pair` (global, variance-based) and
`morris_elementary_effects` (trajectory-based screening). OAT / tornado
is local and still reviewer-mandated in many pharmacology and biophysics
contexts.
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


class TornadoRow(RecipeContract):
    parameter: str
    low_output: float
    high_output: float


class TornadoInput(RecipeContract):
    baseline: float = Field(..., description="output at nominal parameter vector")
    rows: list[TornadoRow] = Field(..., min_length=3)
    output_label: str = "output"
    title: str = "OAT tornado diagram"


def _demo() -> TornadoInput:
    rng = np.random.default_rng(57)
    baseline = 1.00
    names = ["k_on", "V_max", "Km", "k_off", "D", "alpha", "beta"]
    rows = []
    for name in names:
        low_delta = rng.uniform(0.04, 0.42)
        high_delta = rng.uniform(0.04, 0.42)
        # Some parameters invert the direction (low → higher output).
        if name in ("k_off", "Km"):
            low_delta, high_delta = -low_delta, -high_delta
        rows.append(TornadoRow(
            parameter=name,
            low_output=baseline + low_delta,
            high_output=baseline - high_delta,
        ))
    return TornadoInput(
        baseline=baseline, rows=rows, output_label="steady-state activity",
    )


_META = RecipeMetadata(
    name="tornado_diagram",
    modality="sensitivity_analysis",
    family=RecipeFamily.ladder,
    answers_question=(
        "For a one-at-a-time (OAT) sweep, how does the output change "
        "when each parameter is varied to its ±Δ bound?"
    ),
    required_fields=("baseline", "rows"),
    optional_fields=("output_label", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=(
        "sobol_first_total_pair",
        "morris_elementary_effects",
    ),
)


@register_recipe(
    metadata=_META,
    contract=TornadoInput,
    demo_contract=_demo,
)
def render(contract: TornadoInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.6))
    AESTHETIC.apply_to_ax(ax)

    # Sort by total |high-low| descending.
    rows = sorted(
        contract.rows,
        key=lambda r: -(abs(r.high_output - contract.baseline)
                        + abs(r.low_output - contract.baseline)),
    )
    y = np.arange(len(rows))[::-1]
    bar_h = 0.58

    low_color = "#1565C0"
    high_color = "#C62828"

    xs = []
    for yi, r in zip(y, rows):
        lo = r.low_output
        hi = r.high_output
        # Draw halves starting at baseline.
        # Low-side half:
        lo_left = min(lo, contract.baseline)
        lo_w = abs(lo - contract.baseline)
        ax.barh(yi, lo_w, left=lo_left, height=bar_h,
                color=low_color, alpha=0.85, edgecolor="white",
                linewidth=0.7, zorder=3)
        # High-side half:
        hi_left = min(hi, contract.baseline)
        hi_w = abs(hi - contract.baseline)
        ax.barh(yi, hi_w, left=hi_left, height=bar_h,
                color=high_color, alpha=0.85, edgecolor="white",
                linewidth=0.7, zorder=3)
        xs.extend([lo, hi])

        # End-value labels, anchored on the sign side.
        ax.text(lo, yi, f" {smart_fmt(lo)}",
                ha="left" if lo > contract.baseline else "right",
                va="center", fontsize=6.6, color=low_color, zorder=5)
        ax.text(hi, yi, f" {smart_fmt(hi)}",
                ha="left" if hi > contract.baseline else "right",
                va="center", fontsize=6.6, color=high_color, zorder=5)

    # Baseline reference (vertical line, label pinned to upper-left corner
    # of the axes so it never collides with the title).
    ax.axvline(contract.baseline, color="#111111", lw=1.0, zorder=4)
    ax.text(
        0.02, 0.98,
        f"baseline = {smart_fmt(contract.baseline)}",
        transform=ax.transAxes, ha="left", va="top",
        fontsize=7.0, color="#111111",
        bbox=dict(boxstyle="round,pad=0.18", fc="white",
                  ec="#BBBBBB", lw=0.5, alpha=0.95),
        zorder=6,
    )

    xlo = min(xs) - 0.05 * (max(xs) - min(xs))
    xhi = max(xs) + 0.10 * (max(xs) - min(xs))
    ax.set_xlim(xlo, xhi)
    ax.set_yticks(y)
    ax.set_yticklabels([r.parameter for r in rows], fontsize=7.4)
    ax.set_xlabel(contract.output_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Legend pill.
    from matplotlib.patches import Patch
    proxies = [
        Patch(facecolor=high_color, edgecolor="white", label="high-bound sweep"),
        Patch(facecolor=low_color, edgecolor="white", label="low-bound sweep"),
    ]
    ax.legend(handles=proxies, fontsize=6.6, frameon=False,
              loc="lower right", handlelength=1.4)
    return ax
