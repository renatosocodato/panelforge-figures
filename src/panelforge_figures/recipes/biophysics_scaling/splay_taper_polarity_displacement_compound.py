"""Splay-taper / polarity-displacement compound forest — three
auxiliary readouts (splay-to-taper transition, polarity-displacement
offset, splay symmetry) presented as a coef-forest with per-condition
markers + 95% CI ranges; zero-effect reference line.

Coef-forest family: >=3 markers + >=1 reference line.
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
from ._shared import CompoundReadoutRow

_CONDITION_PALETTE = {
    "WT": "#37474F", "LI": "#EF5350",
    "control": "#37474F", "DISC1": "#EF5350",
}


class CompoundReadoutForestInput(RecipeContract):
    rows: list[CompoundReadoutRow] = Field(..., min_length=3)
    title: str = "Splay-taper × polarity-displacement compound"


def _demo() -> CompoundReadoutForestInput:
    rng = np.random.default_rng(708)
    rows: list[CompoundReadoutRow] = []
    spec = [
        # readout, WT mean, LI mean
        ("splay_to_taper_transition", -0.08, 0.42),
        ("polarity_displacement_offset", 0.04, 0.38),
        ("splay_symmetry_index", 0.92, 0.55),
    ]
    for readout, wt_mu, li_mu in spec:
        for cond, mu in (("WT", wt_mu), ("LI", li_mu)):
            vals = rng.normal(mu, abs(mu) * 0.20 + 0.04, 18).tolist()
            ci_half = float(abs(mu) * 0.18 + 0.04)
            rows.append(CompoundReadoutRow(
                readout=readout, condition=cond,
                values=vals,
                ci_lo=float(mu - ci_half),
                ci_hi=float(mu + ci_half),
            ))
    return CompoundReadoutForestInput(rows=rows)


_META = RecipeMetadata(
    name="splay_taper_polarity_displacement_compound",
    modality="biophysics_scaling",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "Across three frontier-architecture readouts (splay-taper "
        "transition, polarity-displacement, splay symmetry), how do "
        "per-condition estimates compare against the zero-effect "
        "reference?"
    ),
    required_fields=("rows",),
    optional_fields=("title",),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("hierarchical_effect_size_ladder",),
)


@register_recipe(
    metadata=_META,
    contract=CompoundReadoutForestInput,
    demo_contract=_demo,
)
def render(contract: CompoundReadoutForestInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.8, 4.0))
    AESTHETIC.apply_to_ax(ax)

    rows = list(contract.rows)
    n = len(rows)
    y = np.arange(n)

    # Zero-effect reference line.
    ax.axvline(0, color="#888888", lw=0.7, ls="--", zorder=2,
               label="zero effect")

    # Per-row banding by readout.
    readouts_in_order: list[str] = []
    for r in rows:
        if r.readout not in readouts_in_order:
            readouts_in_order.append(r.readout)
    palette_readout = ["#F5F7FA", "#EDF1F4", "#F5F7FA"]
    for ri, readout in enumerate(readouts_in_order):
        readout_rows = [(i, r) for i, r in enumerate(rows)
                        if r.readout == readout]
        if not readout_rows:
            continue
        y_lo_band = readout_rows[0][0] - 0.45
        y_hi_band = readout_rows[-1][0] + 0.45
        ax.axhspan(y_lo_band, y_hi_band,
                   facecolor=palette_readout[ri % len(palette_readout)],
                   alpha=0.5, zorder=1)

    bits = []
    for yi, r in zip(y, rows):
        colour = _CONDITION_PALETTE.get(r.condition, "#37474F")
        marker = "o" if r.condition in ("WT", "control") else "s"
        # CI segment.
        ax.plot([r.ci_lo, r.ci_hi], [yi, yi],
                color=colour, lw=1.4, alpha=0.85, zorder=3)
        # Point estimate (median of values).
        median_v = float(np.median(r.values))
        ax.scatter([median_v], [yi], s=44, marker=marker,
                   facecolor=colour, edgecolor="white",
                   linewidth=0.6, zorder=5)
        bits.append(f"{r.readout[:8]}: {smart_fmt(median_v)}")

    tick_labels = [f"{r.condition} · {r.readout}" for r in rows]
    ax.set_yticks(y)
    ax.set_yticklabels(tick_labels, fontsize=6.4)
    ax.invert_yaxis()
    ax.set_xlabel("compound readout (signed)", fontsize=7.0)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor="#888888", markeredgecolor="white",
               markersize=6, label="WT"),
        Line2D([0], [0], marker="s", color="none",
               markerfacecolor="#888888", markeredgecolor="white",
               markersize=6, label="LI"),
        Line2D([0], [0], color="#888888", ls="--", lw=0.7,
               label="zero effect"),
    ]
    ax.legend(handles=handles, fontsize=6.4, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.16),
              ncols=3, handlelength=1.0)

    ax.set_title(
        f"{contract.title}  ·  {len(readouts_in_order)} readouts",
        fontsize=8.2, pad=4,
    )
    return ax
