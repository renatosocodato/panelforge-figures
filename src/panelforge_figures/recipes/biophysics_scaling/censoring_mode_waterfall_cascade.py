"""Censoring-mode waterfall cascade — per-feature estimate + 95% CI
across pre-registered censoring modes laid out as a cascading
waterfall (each row offset right and down) so the per-mode shift
is visually salient.

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
from ._shared import CensoringCascadeRow

_MODE_PALETTE = {
    "default": "#37474F",       # slate
    "loose": "#90A4AE",         # mid grey
    "strict_R2": "#26A69A",     # teal
    "strict_n": "#AB47BC",      # purple
}


class CensoringWaterfallInput(RecipeContract):
    rows: list[CensoringCascadeRow] = Field(..., min_length=4)
    significance_threshold: float = 0.0
    feature_label: str = "actin Lp"
    title: str = "Censoring-mode waterfall cascade"


def _demo() -> CensoringWaterfallInput:
    rng = np.random.default_rng(621)
    rows: list[CensoringCascadeRow] = []
    # Estimate stable in direction (negative — LI ≲ WT) but
    # magnitude sub-threshold across all four censoring rules.
    for mode, threshold, est in (
        ("default", "default rules", -0.18),
        ("loose", "R^2 > 0.5, n >= 30", -0.22),
        ("strict_R2", "R^2 > 0.7, n >= 30", -0.16),
        ("strict_n", "R^2 > 0.5, n >= 60", -0.14),
    ):
        ci_half = 0.18 + rng.uniform(-0.02, 0.04)
        rows.append(CensoringCascadeRow(
            feature="actin_persistence_length_um",
            censoring_mode=mode,
            threshold_label=threshold,
            estimate=float(est + rng.normal(0, 0.015)),
            ci_lo=float(est - ci_half),
            ci_hi=float(est + ci_half),
        ))
    return CensoringWaterfallInput(
        rows=rows,
        significance_threshold=0.0,
        feature_label="actin Lp (LI - WT, Cohen d)",
    )


_META = RecipeMetadata(
    name="censoring_mode_waterfall_cascade",
    modality="biophysics_scaling",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "Across pre-registered censoring modes, does the per-feature "
        "effect estimate retain its sign and magnitude, or does it "
        "collapse under stricter rules?"
    ),
    required_fields=("rows",),
    optional_fields=("significance_threshold", "feature_label", "title"),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("pre_registered_censoring_mode_grid",),
)


@register_recipe(
    metadata=_META,
    contract=CensoringWaterfallInput,
    demo_contract=_demo,
)
def render(contract: CensoringWaterfallInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.0, 4.0))
    AESTHETIC.apply_to_ax(ax)

    rows = list(contract.rows)
    n = len(rows)

    # Reference vertical line at the significance threshold (typically 0).
    ax.axvline(contract.significance_threshold,
               color="#888888", lw=0.7, ls="--", zorder=2,
               label=f"reference at "
                     f"{smart_fmt(contract.significance_threshold)}")

    # Cascading layout: each subsequent row drops down by 1 *and*
    # the band shading offsets slightly right, so the ladder reads
    # like a waterfall.
    bits = []
    for i, r in enumerate(rows):
        y = i
        colour = _MODE_PALETTE.get(r.censoring_mode, "#37474F")
        # Background band for the row (alternating tint).
        if i % 2 == 0:
            ax.axhspan(y - 0.45, y + 0.45,
                       facecolor="#F5F7FA", alpha=0.5, zorder=1)
        # CI segment.
        ax.plot([r.ci_lo, r.ci_hi], [y, y],
                color=colour, lw=2.2, alpha=0.85, zorder=3)
        # Point estimate marker.
        ax.scatter([r.estimate], [y], s=60, marker="o",
                   facecolor=colour, edgecolor="white",
                   linewidth=0.8, zorder=5)
        # Threshold-rule label inside row.
        ax.text(r.ci_hi + 0.02, y, r.threshold_label,
                ha="left", va="center", fontsize=6.4,
                color="#666666", zorder=4)
        # Per-row verdict.
        if r.ci_hi < contract.significance_threshold or \
                r.ci_lo > contract.significance_threshold:
            verdict = "sig"
        else:
            verdict = "n.s."
        bits.append(f"{r.censoring_mode}: "
                    f"{smart_fmt(r.estimate)} ({verdict})")

    ax.set_yticks(range(n))
    ax.set_yticklabels([r.censoring_mode for r in rows], fontsize=7.0)
    ax.invert_yaxis()
    ax.set_xlabel(contract.feature_label, fontsize=7.0)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    # Direction-stability headline.
    signs = {1 if r.estimate > 0 else -1 for r in rows}
    direction_stable = (len(signs) == 1)
    ax.set_title(
        f"{contract.title}  ·  "
        f"direction {'stable' if direction_stable else 'flips'}  ·  "
        + "   ".join(bits),
        fontsize=8.2, pad=4,
    )

    # Legend below.
    ax.legend(fontsize=6.4, frameon=False, loc="upper center",
              bbox_to_anchor=(0.5, -0.10), ncols=1, handlelength=1.0)
    return ax
