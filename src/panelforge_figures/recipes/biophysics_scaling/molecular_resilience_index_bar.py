"""Molecular resilience index bar — single-bar comparison per condition
showing the resilience scalar with multiverse-stability ribbons behind.

Each condition gets one horizontal bar marker on the resilience axis,
with a translucent ribbon spanning the multiverse low/high stability
bounds. ROBUST conditions (where stability_lo > 0) are highlighted
with a thicker bar and a check-glyph inline annotation.

Coef-forest family: >=3 markers + >=1 reference line. Satisfied by
≥3 condition resilience markers + zero-resilience reference + ROBUST
threshold reference.
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
from ._shared import ResilienceIndexEntry


class MolecularResilienceIndexInput(RecipeContract):
    entries: list[ResilienceIndexEntry] = Field(..., min_length=3)
    robust_threshold: float = 0.50
    title: str = "Molecular resilience index"


def _demo() -> MolecularResilienceIndexInput:
    rng = np.random.default_rng(832)
    # Manuscript F4J values: F-CTL = 0.82; F-CKO = 0.42;
    # M-CTL = 0.65; M-CKO = 0.18.
    rows = [
        ("female · CTL",  0.82, True),
        ("female · CKO",  0.42, False),
        ("male · CTL",    0.65, True),
        ("male · CKO",    0.18, False),
        ("WT · vehicle",  0.75, True),
        ("WT · rescue",   0.55, True),
    ]
    entries: list[ResilienceIndexEntry] = []
    for cond, idx, robust in rows:
        # Multiverse spread: tighter (smaller ribbon) for robust rows.
        w = 0.06 if robust else 0.14
        w_jitter = w + rng.uniform(0.0, 0.03)
        entries.append(ResilienceIndexEntry(
            condition=cond,
            resilience_index=idx,
            stability_lo=max(-1.0, idx - w_jitter),
            stability_hi=min(1.0, idx + w_jitter),
            is_robust=robust,
        ))
    return MolecularResilienceIndexInput(entries=entries)


_META = RecipeMetadata(
    name="molecular_resilience_index_bar",
    modality="biophysics_scaling",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "Per condition, what is the molecular resilience index, "
        "how stable is it across multiverse specifications, and which "
        "conditions are classified as ROBUST?"
    ),
    required_fields=("entries",),
    optional_fields=("robust_threshold", "title"),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=(
        "confinement_energy_gauge_per_genotype",
        "censoring_mode_waterfall_cascade",
    ),
)


@register_recipe(
    metadata=_META,
    contract=MolecularResilienceIndexInput,
    demo_contract=_demo,
)
def render(contract: MolecularResilienceIndexInput, ax=None, **_):
    import matplotlib.patches as mpatches
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.6))
    AESTHETIC.apply_to_ax(ax)

    entries = list(contract.entries)
    n = len(entries)
    y = np.arange(n)[::-1]

    # Reference 1: zero resilience.
    ax.axvline(0.0, color="#888888", lw=0.7, ls="--", zorder=1,
               label="zero resilience")
    # Reference 2: ROBUST threshold.
    ax.axvline(contract.robust_threshold, color="#26A69A",
               lw=0.7, ls=":", zorder=1,
               label=f"ROBUST threshold = "
                     f"{smart_fmt(contract.robust_threshold)}")

    robust_color = "#26A69A"
    fragile_color = "#9E9E9E"

    for yi, e in zip(y, entries):
        colour = robust_color if e.is_robust else fragile_color
        # Multiverse-stability ribbon.
        ax.add_patch(mpatches.Rectangle(
            (e.stability_lo, yi - 0.30),
            e.stability_hi - e.stability_lo, 0.60,
            facecolor=colour, edgecolor="none",
            alpha=0.18, zorder=2,
        ))
        # Resilience-index marker (the >=3 markers for the family rule).
        ax.plot([0.0, e.resilience_index], [yi, yi],
                color=colour, lw=1.4 if e.is_robust else 1.0,
                alpha=0.92, zorder=3)
        ax.scatter([e.resilience_index], [yi],
                   s=66 if e.is_robust else 44,
                   marker="o" if e.is_robust else "s",
                   facecolor=colour, edgecolor="white",
                   linewidth=0.7, zorder=5)
        # Right-margin index callout + ROBUST check.
        check = " [R]" if e.is_robust else ""
        ax.text(max(e.stability_hi, e.resilience_index) + 0.02, yi,
                f"{smart_fmt(e.resilience_index)}{check}",
                ha="left", va="center", fontsize=6.4,
                color=colour, fontweight="bold", zorder=6)

    ax.set_yticks(y)
    ax.set_yticklabels([e.condition for e in entries], fontsize=7.0)
    ax.set_xlim(-0.05, 1.10)
    ax.set_xlabel("resilience index (multiverse stability ribbon)")
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], marker="o", color=robust_color, lw=1.4,
               markerfacecolor=robust_color, markeredgecolor="white",
               markersize=7, label="ROBUST [R]"),
        Line2D([0], [0], marker="s", color=fragile_color, lw=1.0,
               markerfacecolor=fragile_color, markeredgecolor="white",
               markersize=6, label="fragile / non-sig"),
        Line2D([0], [0], color="#888888", ls="--", lw=0.7,
               label="zero resilience"),
        Line2D([0], [0], color=robust_color, ls=":", lw=0.7,
               label="ROBUST threshold"),
    ]
    ax.legend(handles=handles, fontsize=6.4, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.14),
              ncols=4, handlelength=1.2)

    n_robust = sum(1 for e in entries if e.is_robust)
    ax.set_title(
        f"{contract.title}  ·  {n_robust}/{n} conditions ROBUST",
        fontsize=8.2, pad=4,
    )
    return ax
