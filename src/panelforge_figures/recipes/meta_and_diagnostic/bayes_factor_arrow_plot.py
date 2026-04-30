"""Bayes factor arrow plot — per-row arrow markers showing BF_01
with Wagenmakers / Kass-Raftery threshold bands and a vertical
reference at BF=1 (no evidence either way).

Coef-forest family: >=3 markers + >=1 reference line.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    bf_from_bic,
    classify_bf_threshold,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC
from ._shared import BayesFactorRow

_TIER_COLOR = {
    "favours_alt": "#C62828",   # red — evidence against null
    "anecdotal": "#FB8C00",     # orange — barely-there evidence for null
    "moderate": "#FBC02D",      # amber
    "strong": "#7CB342",        # light green
    "decisive": "#2E7D32",      # green — decisive null
}

_THRESHOLD_LINES = (
    (1.0, "anecdotal"),
    (3.0, "moderate"),
    (10.0, "strong"),
    (30.0, "decisive"),
)


class BayesFactorArrowInput(RecipeContract):
    rows: list[BayesFactorRow] = Field(..., min_length=3)
    title: str = "Bayes factor arrow plot"


def _demo() -> BayesFactorArrowInput:
    rng = np.random.default_rng(801)
    rows: list[BayesFactorRow] = []
    spec = [
        # label, bic_alt, bic_null
        ("power_spectral_density", 102.4, 98.9),     # null wins (BF~5.7)
        ("sample_entropy", 100.7, 97.5),             # null wins (BF~4.8)
        ("recurrence_summary", 99.0, 97.0),          # null wins (BF~2.7)
        ("acf_lag1", 96.0, 99.0),                    # alt wins (BF<1)
    ]
    for label, b_a, b_n in spec:
        bf = bf_from_bic(b_a, b_n)
        rows.append(BayesFactorRow(
            label=label, bic_alt=float(b_a), bic_null=float(b_n),
            bf_01=float(bf),
            threshold_class=classify_bf_threshold(bf),
        ))
    _ = rng.normal(0, 0.05, 1)
    return BayesFactorArrowInput(rows=rows)


_META = RecipeMetadata(
    name="bayes_factor_arrow_plot",
    modality="meta_and_diagnostic",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "Per descriptor, how strong is the Bayes-factor evidence "
        "for the null hypothesis vs the alternative, and which "
        "Wagenmakers / Kass-Raftery threshold tier does it cross?"
    ),
    required_fields=("rows",),
    optional_fields=("title",),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("heterogeneity_forest",),
)


@register_recipe(
    metadata=_META,
    contract=BayesFactorArrowInput,
    demo_contract=_demo,
)
def render(contract: BayesFactorArrowInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.0, 3.8))
    AESTHETIC.apply_to_ax(ax)

    rows = list(contract.rows)
    n = len(rows)
    y = np.arange(n)

    # Threshold bands (vertical axhspan-style on log-x).  BF axis is
    # log-scale because BF spans orders of magnitude.
    for x_lo, name in _THRESHOLD_LINES:
        ax.axvline(x_lo, color="#CCCCCC", lw=0.7, ls="--", zorder=2)

    # Reference line at BF = 1 (no evidence either way) — bold dashed.
    ax.axvline(1.0, color="#888888", lw=0.9, ls="--", zorder=3,
               label="BF = 1 (no evidence)")

    # Per-row arrow markers.
    for yi, r in zip(y, rows):
        colour = _TIER_COLOR.get(r.threshold_class, "#37474F")
        # Tail at BF=1, head at observed BF — direction shows
        # which side wins.
        bf = max(r.bf_01, 1e-6)
        ax.annotate(
            "", xy=(bf, yi), xytext=(1.0, yi),
            arrowprops=dict(
                arrowstyle="->", color=colour, lw=2.2,
                shrinkA=0, shrinkB=0,
            ),
            zorder=5,
        )
        ax.scatter([bf], [yi], s=44, marker="o",
                   facecolor=colour, edgecolor="white",
                   linewidth=0.5, zorder=6)
        # Inline BF + tier label.
        ax.text(bf * 1.6 if bf < 1.0 else bf * 1.15, yi,
                f"BF={smart_fmt(bf)}  ·  {r.threshold_class}",
                ha="left", va="center", fontsize=6.4,
                color=colour, zorder=7)

    # Threshold zone labels along the top.
    band_x = [0.5, 2.0, 5.5, 17.5, 60.0]
    band_lab = ["favours alt", "anecdotal", "moderate",
                "strong", "decisive"]
    band_col = ["favours_alt", "anecdotal", "moderate",
                "strong", "decisive"]
    for x_lab, lab, key in zip(band_x, band_lab, band_col):
        ax.text(x_lab, -0.6, lab,
                ha="center", va="bottom", fontsize=6.0,
                color=_TIER_COLOR.get(key, "#888888"),
                style="italic", zorder=4)

    ax.set_yticks(y)
    ax.set_yticklabels([r.label for r in rows], fontsize=6.6)
    ax.invert_yaxis()
    ax.set_xscale("log")
    ax.set_xlim(0.1, 100.0)
    ax.set_xlabel("Bayes factor BF$_{01}$ (favours null when > 1)")
    ax.grid(axis="x", which="major", color="#EEEEEE",
            lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    n_decisive = sum(1 for r in rows
                     if r.threshold_class in ("strong", "decisive"))
    ax.set_title(
        f"{contract.title}  ·  {n} descriptors  ·  "
        f"{n_decisive} ≥ strong-null",
        fontsize=8.4, pad=14,
    )
    return ax
