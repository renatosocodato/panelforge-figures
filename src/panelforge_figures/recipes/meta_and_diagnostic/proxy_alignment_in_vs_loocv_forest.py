"""Proxy alignment in-sample vs LOOCV forest — paired-R² horizontal
forest comparing in-sample fit (full model) against
leave-one-out cross-validated fit per proxy / readout. Negative
LOOCV R² flagged as overfit.

Coef-forest family: >=3 markers + >=1 reference line.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    StatisticalContract,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC
from ._shared import ProxyAlignmentEntry


class ProxyAlignmentInput(RecipeContract):
    entries: list[ProxyAlignmentEntry] = Field(..., min_length=3)
    title: str = "Proxy alignment: in-sample vs LOOCV"


def _demo() -> ProxyAlignmentInput:
    rng = np.random.default_rng(806)
    entries: list[ProxyAlignmentEntry] = [
        ProxyAlignmentEntry(
            proxy="vel_sd", in_sample_R2=0.895, loocv_R2=0.593,
            p_value=0.015, n_units=15,
        ),
        ProxyAlignmentEntry(
            proxy="retraction_fraction",
            in_sample_R2=0.400, loocv_R2=0.216,
            p_value=0.082, n_units=15,
        ),
        ProxyAlignmentEntry(
            proxy="extension_fraction",
            in_sample_R2=0.161, loocv_R2=-0.142,
            p_value=0.412, n_units=15,
        ),
        ProxyAlignmentEntry(
            proxy="mean_velocity",
            in_sample_R2=0.024, loocv_R2=-2.118,
            p_value=0.832, n_units=15,
        ),
    ]
    _ = rng.normal(0, 0.05, 1)
    return ProxyAlignmentInput(entries=entries)


_META = RecipeMetadata(
    name="proxy_alignment_in_vs_loocv_forest",
    modality="meta_and_diagnostic",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "Per proxy / readout, how does in-sample R² compare to "
        "leave-one-out cross-validated R², and which proxies show "
        "the strongest alignment vs the strongest overfit?"
    ),
    required_fields=("entries",),
    optional_fields=("title",),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("competing_model_residual_panels",),
    statistical_contract=StatisticalContract(
        min_n_per_group=10,
        independence="paired",
        refuses_when=("missing_paired_structure",),
    ),
)


@register_recipe(
    metadata=_META,
    contract=ProxyAlignmentInput,
    demo_contract=_demo,
)
def render(contract: ProxyAlignmentInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.0, 3.8))
    AESTHETIC.apply_to_ax(ax)

    entries = list(contract.entries)
    # Sort by LOOCV R² descending (best generalisation first).
    entries.sort(key=lambda e: -e.loocv_R2)
    n = len(entries)
    y = np.arange(n)

    # Reference at R² = 0 (no predictive power).
    ax.axvline(0, color="#888888", lw=0.7, ls="--", zorder=2,
               label="R² = 0 (no predictive value)")

    # Per-row connecting line + paired markers.
    for yi, e in zip(y, entries):
        # Connecting line between in-sample and LOOCV.
        x_lo = min(e.in_sample_R2, e.loocv_R2)
        x_hi = max(e.in_sample_R2, e.loocv_R2)
        # Colour by overfit severity: red if LOOCV negative.
        gap_colour = "#C62828" if e.loocv_R2 < 0 else "#888888"
        ax.plot([x_lo, x_hi], [yi, yi],
                color=gap_colour, lw=1.0, alpha=0.65, zorder=3)
        # In-sample marker (filled circle).
        ax.scatter([e.in_sample_R2], [yi],
                   s=54, marker="o",
                   facecolor="#37474F", edgecolor="white",
                   linewidth=0.6, zorder=5)
        # LOOCV marker (hollow square).
        ax.scatter([e.loocv_R2], [yi],
                   s=54, marker="s",
                   facecolor="white", edgecolor="#37474F",
                   linewidth=1.4, zorder=5)
        # Overfit flag — placed to the right of the rightmost
        # marker so it never overlaps the y-tick label area, even
        # when LOOCV R^2 is strongly negative.
        if e.loocv_R2 < 0:
            x_flag = max(e.in_sample_R2, e.loocv_R2) + 0.06
            ax.text(x_flag, yi, "OVERFIT",
                    ha="left", va="center", fontsize=6.0,
                    color="#C62828", fontweight="bold", zorder=6)

    tick_labels = []
    for e in entries:
        bits = (f"{e.proxy}  "
                f"(Δ = {smart_fmt(e.in_sample_R2 - e.loocv_R2)})")
        tick_labels.append(bits)
    ax.set_yticks(y)
    ax.set_yticklabels(tick_labels, fontsize=6.6)
    ax.invert_yaxis()
    ax.set_xlabel("R²")
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor="#37474F", markeredgecolor="white",
               markersize=6, label="in-sample"),
        Line2D([0], [0], marker="s", color="none",
               markerfacecolor="white", markeredgecolor="#37474F",
               markersize=6, label="LOOCV"),
        Line2D([0], [0], color="#888888", ls="--", lw=0.7,
               label="R² = 0"),
    ]
    ax.legend(handles=handles, fontsize=6.4, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.16),
              ncols=3, handlelength=1.0)

    n_overfit = sum(1 for e in entries if e.loocv_R2 < 0)
    n_aligned = sum(
        1 for e in entries
        if e.loocv_R2 > 0 and abs(e.in_sample_R2 - e.loocv_R2) < 0.30
    )
    ax.set_title(
        f"{contract.title}  ·  n = {n} proxies  ·  "
        f"{n_aligned} aligned  ·  {n_overfit} overfit",
        fontsize=8.2, pad=4,
    )
    return ax
