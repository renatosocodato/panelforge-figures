"""z-span vs width with Euler threshold — per-cell scatter of
out-of-plane deflection (z-span) against protrusion width, with
the Euler critical-length curve drawn as a dashed reference;
points colour-coded by genotype.

Scatter-collapse family: >=1 scatter + >=1 fit line.
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
from ._shared import ZSpanWidthSample

_CONDITION_PALETTE = {
    "WT": "#37474F", "LI": "#EF5350",
    "control": "#37474F", "DISC1": "#EF5350",
}


class ZSpanWidthEulerInput(RecipeContract):
    samples: list[ZSpanWidthSample] = Field(..., min_length=4)
    title: str = "z-span vs width with Euler threshold"


def _demo() -> ZSpanWidthEulerInput:
    rng = np.random.default_rng(681)
    samples: list[ZSpanWidthSample] = []
    for cond, w_mu, z_mu in (
        ("WT", 4.0, 0.4),
        ("LI", 2.1, 1.0),
    ):
        for k in range(20):
            w = float(max(0.5, rng.normal(w_mu, w_mu * 0.18)))
            # Euler L_crit is roughly proportional to w (for fixed Lp).
            # Use a representative Euler threshold curve L_crit = c * w.
            l_crit = float(0.32 * w)
            z = float(max(0.05, rng.normal(z_mu, z_mu * 0.30)))
            samples.append(ZSpanWidthSample(
                cell_id=f"{cond}_{k:02d}",
                condition=cond,
                width_um=w,
                z_span_um=z,
                euler_l_crit_um=l_crit,
            ))
    return ZSpanWidthEulerInput(samples=samples)


_META = RecipeMetadata(
    name="z_span_vs_width_with_euler_threshold",
    modality="biophysics_scaling",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Per cell, how does out-of-plane deflection (z-span) "
        "scale with protrusion width, and which cells exceed "
        "the Euler critical-length threshold (supercritical)?"
    ),
    required_fields=("samples",),
    optional_fields=("title",),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("euler_critical_length_crossing_distribution",),
)


@register_recipe(
    metadata=_META,
    contract=ZSpanWidthEulerInput,
    demo_contract=_demo,
)
def render(contract: ZSpanWidthEulerInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.8, 4.0))
    AESTHETIC.apply_to_ax(ax)

    widths = np.array([s.width_um for s in contract.samples])
    z_spans = np.array([s.z_span_um for s in contract.samples])
    euler = np.array([s.euler_l_crit_um for s in contract.samples])
    conditions_arr = [s.condition for s in contract.samples]

    # Euler threshold curve (dashed coral).
    w_grid = np.linspace(min(widths.min() * 0.9, 0.5),
                         max(widths.max() * 1.1, 5.0), 60)
    # Use median proportionality coefficient from the data.
    coeff = float(np.median(euler / widths)) if widths.size > 0 else 0.32
    l_crit_curve = coeff * w_grid
    ax.plot(w_grid, l_crit_curve,
            color="#EF6C00", lw=1.4, ls="--", zorder=3,
            label=f"Euler L_crit = {smart_fmt(coeff)} · w")

    # Per-cell scatter coloured by genotype.
    conditions = list(dict.fromkeys(conditions_arr))
    bits = []
    for cond in conditions:
        mask = np.array([c == cond for c in conditions_arr])
        colour = _CONDITION_PALETTE.get(cond, "#37474F")
        ax.scatter(widths[mask], z_spans[mask],
                   s=44, color=colour, edgecolor="white",
                   linewidth=0.6, alpha=0.85, zorder=5, label=cond)
        # Supercritical fraction (z_span > Euler L_crit at that width).
        n_super = int((z_spans[mask] > euler[mask]).sum())
        n_total = int(mask.sum())
        bits.append(f"{cond}: {n_super}/{n_total} supercritical")

    ax.set_xlabel("protrusion width (um)")
    ax.set_ylabel("z-span (um)")
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.4)

    ax.set_title(
        f"{contract.title}  ·  " + "   ".join(bits),
        fontsize=8.2, pad=4,
    )
    return ax
