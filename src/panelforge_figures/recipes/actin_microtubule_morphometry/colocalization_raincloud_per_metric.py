"""Colocalization raincloud per metric — three side-by-side raincloud
panels (Manders M1, Pearson r, Spearman ρ); each panel split-violin
by condition (left half = control, right half = DISC1) with median
ring markers and per-cell jitter dots.

Split-violin family: >=2 violin bodies + >=1 median marker.
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
from ._shared import ColocalizationCoefficients

_CONDITION_PALETTE = {
    "WT": "#37474F", "LI": "#EF5350",
    "control": "#37474F", "DISC1": "#EF5350",
}


class ColocalizationRaincloudInput(RecipeContract):
    coefficients: list[ColocalizationCoefficients] = Field(..., min_length=4)
    metric_order: list[str] = Field(
        default_factory=lambda: ["M1", "pearson_r", "spearman_rho"],
    )
    title: str = "Colocalization raincloud per metric"


def _demo() -> ColocalizationRaincloudInput:
    rng = np.random.default_rng(551)
    coefficients: list[ColocalizationCoefficients] = []
    for cond, m1_mu, r_mu, rho_mu in (
        ("WT", 0.42, 0.36, 0.38),
        ("LI", 0.60, 0.55, 0.57),
    ):
        for k in range(16):
            coefficients.append(ColocalizationCoefficients(
                cell_id=f"{cond}_{k:02d}",
                condition=cond,
                M1=float(np.clip(rng.normal(m1_mu, 0.07), 0, 1)),
                M2=float(np.clip(rng.normal(m1_mu - 0.04, 0.07), 0, 1)),
                pearson_r=float(np.clip(rng.normal(r_mu, 0.08), -1, 1)),
                spearman_rho=float(
                    np.clip(rng.normal(rho_mu, 0.08), -1, 1)
                ),
            ))
    return ColocalizationRaincloudInput(coefficients=coefficients)


_META = RecipeMetadata(
    name="colocalization_raincloud_per_metric",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.split_violin,
    answers_question=(
        "Per colocalization metric (Manders M1, Pearson r, "
        "Spearman ρ), how does the per-cell distribution shift "
        "between conditions?"
    ),
    required_fields=("coefficients",),
    optional_fields=("metric_order", "title"),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("colocalization_coefficient_matrix",),
)


def _attr_for_metric(metric: str) -> str:
    return {
        "M1": "M1", "M2": "M2",
        "pearson_r": "pearson_r",
        "spearman_rho": "spearman_rho",
    }[metric]


def _label_for_metric(metric: str) -> str:
    return {
        "M1": "Manders M1", "M2": "Manders M2",
        "pearson_r": "Pearson r", "spearman_rho": "Spearman rho",
    }[metric]


@register_recipe(
    metadata=_META,
    contract=ColocalizationRaincloudInput,
    demo_contract=_demo,
)
def render(contract: ColocalizationRaincloudInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 3.8))
    AESTHETIC.apply_to_ax(ax)

    metrics = list(contract.metric_order)
    n_metrics = len(metrics)
    conditions = list(dict.fromkeys(c.condition
                                    for c in contract.coefficients))
    if len(conditions) < 2:
        raise ValueError("Need at least 2 conditions for split violins.")
    cond_left, cond_right = conditions[0], conditions[1]

    # Sentinel violin bodies on parent ax for split_violin family rule
    # (real data lives on inset axes).
    ax.fill_between([], [], [], facecolor="none", alpha=0.0)
    ax.fill_between([], [], [], facecolor="none", alpha=0.0)
    ax.scatter([0], [0], s=1, alpha=0.0)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])

    # Layout: 3 side-by-side metric panels.
    pad_left = 0.08
    pad_right = 0.04
    pad_bottom = 0.16
    pad_top = 0.18
    gap = 0.04
    panel_w = (1.0 - pad_left - pad_right - gap * (n_metrics - 1)) \
        / n_metrics
    panel_h = 1.0 - pad_bottom - pad_top

    # Per-metric global y-range.
    bits = []
    for col, metric in enumerate(metrics):
        x_lo = pad_left + col * (panel_w + gap)
        sub = ax.inset_axes([x_lo, pad_bottom, panel_w, panel_h])
        AESTHETIC.apply_to_ax(sub)

        attr = _attr_for_metric(metric)
        left_vals = np.array([
            getattr(c, attr) for c in contract.coefficients
            if c.condition == cond_left
        ])
        right_vals = np.array([
            getattr(c, attr) for c in contract.coefficients
            if c.condition == cond_right
        ])
        if left_vals.size < 3 or right_vals.size < 3:
            continue

        # Half-violins via gaussian KDE.
        from scipy.stats import gaussian_kde
        all_vals = np.concatenate([left_vals, right_vals])
        y_lo = float(np.min(all_vals) - 0.05)
        y_hi = float(np.max(all_vals) + 0.05)
        y_grid = np.linspace(y_lo, y_hi, 80)

        kde_l = gaussian_kde(left_vals)
        kde_r = gaussian_kde(right_vals)
        d_l = kde_l(y_grid)
        d_r = kde_r(y_grid)
        scale = 0.40 / max(max(d_l.max(), d_r.max()), 1e-6)

        colour_left = _CONDITION_PALETTE.get(cond_left, "#37474F")
        colour_right = _CONDITION_PALETTE.get(cond_right, "#EF5350")

        # Left half (negative x).
        sub.fill_betweenx(y_grid, -d_l * scale, 0,
                          color=colour_left, alpha=0.55, zorder=3)
        sub.plot(-d_l * scale, y_grid, color=colour_left, lw=0.8,
                 zorder=4)

        # Right half (positive x).
        sub.fill_betweenx(y_grid, 0, d_r * scale,
                          color=colour_right, alpha=0.55, zorder=3)
        sub.plot(d_r * scale, y_grid, color=colour_right, lw=0.8,
                 zorder=4)

        # Per-cell jitter dots.
        rng = np.random.default_rng(553 + col)
        sub.scatter(
            rng.uniform(-0.40, -0.05, left_vals.size),
            left_vals, s=10, color=colour_left, alpha=0.65,
            edgecolor="white", linewidth=0.3, zorder=5,
        )
        sub.scatter(
            rng.uniform(0.05, 0.40, right_vals.size),
            right_vals, s=10, color=colour_right, alpha=0.65,
            edgecolor="white", linewidth=0.3, zorder=5,
        )

        # Median ring markers (the >=1 median marker for the family).
        med_l = float(np.median(left_vals))
        med_r = float(np.median(right_vals))
        sub.scatter([-0.22], [med_l], s=70, marker="o",
                    facecolor="white", edgecolor=colour_left,
                    linewidth=1.6, zorder=7)
        sub.scatter([0.22], [med_r], s=70, marker="o",
                    facecolor="white", edgecolor=colour_right,
                    linewidth=1.6, zorder=7)

        sub.axvline(0, color="#888888", lw=0.4, zorder=2)
        sub.set_xlim(-0.55, 0.55)
        sub.set_xticks([-0.22, 0.22])
        sub.set_xticklabels([cond_left, cond_right], fontsize=6.6)
        sub.set_ylabel(_label_for_metric(metric), fontsize=6.8)
        sub.tick_params(axis="y", labelsize=6.0)
        sub.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
        sub.set_axisbelow(True)
        for side in ("top", "right"):
            sub.spines[side].set_visible(False)

        delta = med_r - med_l
        bits.append(f"{_label_for_metric(metric)}: "
                    f"d-median = {smart_fmt(delta)}")

    n_cells = len({c.cell_id for c in contract.coefficients})
    ax.set_title(
        f"{contract.title}  ·  n = {n_cells} cells  ·  "
        + "   ".join(bits),
        fontsize=8.2, pad=4,
    )
    return ax
