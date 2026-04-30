"""Dual-scale significance lollipop — diverging lollipop of -log10(p)
at multiple scales (whole-cell vs protrusion-internal) per metric,
row-banded by domain tier (polymer / network / territory).

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
from ._shared import MultiScaleSignificanceRow

_TIER_PALETTE = {
    "polymer": "#E91E63",       # actin pink
    "network": "#00BCD4",       # MT cyan
    "territory": "#FFC107",     # amber
    "geometry": "#37474F",      # slate
    "whole_cell": "#9E9E9E",    # mid grey
}

_SCALE_MARKER = {
    "whole_cell": "o",
    "protrusion_internal": "s",
}


class DualScaleSignificanceLollipopInput(RecipeContract):
    rows: list[MultiScaleSignificanceRow] = Field(..., min_length=6)
    significance_threshold: float = 0.05
    title: str = "Dual-scale significance lollipop"


def _demo() -> DualScaleSignificanceLollipopInput:
    rng = np.random.default_rng(501)
    # 12 metrics × 2 scales × 3 tiers (polymer / network / territory).
    spec = [
        # tier, feature, p_whole_cell, p_protrusion_internal
        ("polymer", "Lp_actin", 0.42, 0.31),
        ("polymer", "Lp_mt", 0.55, 0.40),
        ("polymer", "fractal_dim_actin", 0.38, 0.27),
        ("polymer", "fractal_dim_mt", 0.61, 0.48),
        ("network", "coherency", 0.10, 0.0010),
        ("network", "MT_density", 0.07, 0.00045),
        ("network", "branch_count", 0.05, 0.0008),
        ("network", "polarity_offset", 0.21, 0.012),
        ("territory", "contact_fraction", 0.0011, 0.00007),
        ("territory", "desert_fraction", 0.0035, 0.00021),
        ("territory", "MT_overlap", 0.013, 0.0001),
        ("territory", "stand_off_distance", 0.0018, 0.0017),
    ]
    rows: list[MultiScaleSignificanceRow] = []
    for tier, feature, p_wc, p_pr in spec:
        for scale, p in (("whole_cell", p_wc),
                         ("protrusion_internal", p_pr)):
            rows.append(MultiScaleSignificanceRow(
                feature=feature, scale=scale,
                neg_log10_p=float(-np.log10(p) + rng.normal(0, 0.04)),
                tier=tier,
                direction="up" if "contact" in feature
                or "MT" in feature else "down",
            ))
    return DualScaleSignificanceLollipopInput(rows=rows)


_META = RecipeMetadata(
    name="dual_scale_significance_lollipop",
    modality="biophysics_scaling",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "Across multiple scales (whole-cell vs protrusion-internal) "
        "and tier-bands (polymer / network / territory), where do "
        "metrics sharpen significance?"
    ),
    required_fields=("rows",),
    optional_fields=("significance_threshold", "title"),
    file_format_hints=("csv", "yaml"),
    alternatives_in_modality=("hierarchical_effect_size_ladder",),
)


@register_recipe(
    metadata=_META,
    contract=DualScaleSignificanceLollipopInput,
    demo_contract=_demo,
)
def render(contract: DualScaleSignificanceLollipopInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 4.4))
    AESTHETIC.apply_to_ax(ax)

    # Group rows by (tier, feature) so the same feature appears once
    # on the y-axis with multiple scale lollipops at the same y.
    features_in_order: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for r in contract.rows:
        key = (r.tier, r.feature)
        if key not in seen:
            features_in_order.append(key)
            seen.add(key)

    # Sort by tier (polymer → network → territory → geometry → other),
    # then preserve insertion order within tier.  Capture insertion
    # rank BEFORE sort so the secondary key remains valid.
    tier_order = {"polymer": 0, "network": 1, "territory": 2,
                  "geometry": 3, "whole_cell": 4}
    insertion_rank = {k: idx for idx, k in enumerate(features_in_order)}
    features_in_order.sort(
        key=lambda k: (tier_order.get(k[0], 99), insertion_rank[k]),
    )

    n = len(features_in_order)
    y_idx = {fk: i for i, fk in enumerate(features_in_order)}

    # Reference line at -log10(threshold).
    ref_x = float(-np.log10(contract.significance_threshold))
    ax.axvline(ref_x, color="#888888", lw=0.7, ls="--", zorder=2,
               label=f"p = {smart_fmt(contract.significance_threshold)}")

    # Tier-band background.
    tier_runs: list[tuple[str, int, int]] = []
    if features_in_order:
        cur_tier = features_in_order[0][0]
        cur_start = 0
        for i, (t, _) in enumerate(features_in_order):
            if t != cur_tier:
                tier_runs.append((cur_tier, cur_start, i - 1))
                cur_tier = t
                cur_start = i
        tier_runs.append((cur_tier,
                          cur_start, len(features_in_order) - 1))
    for t, lo, hi in tier_runs:
        colour = _TIER_PALETTE.get(t, "#888888")
        ax.axhspan(lo - 0.5, hi + 0.5,
                   color=colour, alpha=0.06, zorder=1)
        # Tier label at right edge (axes-fraction outside data zone).
        y_mid_data = (lo + hi) / 2.0
        # Inverted axis: data y=-0.5 -> axes y=1.0; data y=n-0.5 -> axes y=0.0
        y_axes_frac = 1.0 - (y_mid_data + 0.5) / n
        ax.text(1.005, y_axes_frac, t,
                transform=ax.transAxes,
                ha="left", va="center", fontsize=6.4,
                color=colour, fontweight="bold",
                style="italic", zorder=3)

    # Per-row lollipops.
    for r in contract.rows:
        yi = y_idx[(r.tier, r.feature)]
        marker = _SCALE_MARKER.get(r.scale, "D")
        colour = _TIER_PALETTE.get(r.tier, "#888888")
        # Lollipop stick from x=0 to x=neg_log10_p.
        ax.plot([0, r.neg_log10_p], [yi, yi],
                color=colour, lw=0.9, alpha=0.55, zorder=3)
        ax.scatter([r.neg_log10_p], [yi],
                   s=44, marker=marker,
                   facecolor=colour, edgecolor="white",
                   linewidth=0.5, zorder=5)

    ax.set_yticks(range(n))
    ax.set_yticklabels([f for _, f in features_in_order], fontsize=6.6)
    ax.invert_yaxis()
    ax.set_xlabel("-log10(p)", labelpad=4)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.set_ylim(n - 0.5, -0.5)

    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor="#888888", markeredgecolor="white",
               markersize=6, label="whole-cell"),
        Line2D([0], [0], marker="s", color="none",
               markerfacecolor="#888888", markeredgecolor="white",
               markersize=6, label="protrusion-internal"),
        Line2D([0], [0], color="#888888", ls="--", lw=0.7,
               label=f"p = {smart_fmt(contract.significance_threshold)}"),
    ]
    ax.legend(handles=handles, fontsize=6.4, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.18),
              ncols=3, handlelength=1.0)

    # Headline: how many features sharpen at protrusion-internal scale.
    pr_strong = sum(
        1 for r in contract.rows
        if r.scale == "protrusion_internal" and r.neg_log10_p > ref_x
    )
    wc_strong = sum(
        1 for r in contract.rows
        if r.scale == "whole_cell" and r.neg_log10_p > ref_x
    )
    ax.set_title(
        f"{contract.title}  ·  whole-cell {wc_strong} sig  ·  "
        f"protrusion-internal {pr_strong} sig",
        fontsize=8.2, pad=4,
    )
    return ax
