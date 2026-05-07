"""Confinement ratio distribution by genotype — split-violin
distribution of per-cell confinement ratio (z-span / Euler L_crit)
per genotype; horizontal reference at ratio = 1.0 (super-/sub-
critical boundary); per-genotype supercritical fraction in title.

Split-violin family: >=2 violin bodies + >=1 median marker.
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
from ._shared import ConfinementRatioSample

_CONDITION_PALETTE = {
    "WT": "#37474F", "LI": "#EF5350",
    "control": "#37474F", "DISC1": "#EF5350",
}


class ConfinementRatioInput(RecipeContract):
    samples: list[ConfinementRatioSample] = Field(..., min_length=4)
    threshold: float = 1.0
    title: str = "Confinement ratio by genotype"


def _demo() -> ConfinementRatioInput:
    rng = np.random.default_rng(707)
    samples: list[ConfinementRatioSample] = []
    for cond, mu, n in (
        ("WT", 0.55, 30),
        ("LI", 1.55, 30),
    ):
        for k in range(n):
            ratio = float(max(0.05, rng.normal(mu, mu * 0.30)))
            samples.append(ConfinementRatioSample(
                cell_id=f"{cond}_{k:02d}", condition=cond,
                ratio=ratio,
            ))
    return ConfinementRatioInput(samples=samples)


_META = RecipeMetadata(
    name="confinement_ratio_distribution_by_genotype",
    modality="biophysics_scaling",
    family=RecipeFamily.split_violin,
    answers_question=(
        "Per genotype, how is the confinement ratio (z-span / Euler "
        "L_crit) distributed, and what fraction of cells exceed the "
        "supercritical threshold (ratio > 1.0)?"
    ),
    required_fields=("samples",),
    optional_fields=("threshold", "title"),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("z_span_vs_width_with_euler_threshold",),
    statistical_contract=StatisticalContract(
        min_n_per_group=10,
        distribution_assumption="approximately_gaussian",
        multiple_comparisons="any_correction_required",
        independence="iid",
        effect_size_in_units="standardized_d",
        rendered_claim_template="Cohen's d = {d:.2f} ({outcome_class})",
        refuses_when=("underpowered",),
    ),
)


@register_recipe(
    metadata=_META,
    contract=ConfinementRatioInput,
    demo_contract=_demo,
)
def render(contract: ConfinementRatioInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.8))
    AESTHETIC.apply_to_ax(ax)

    conditions = list(dict.fromkeys(s.condition for s in contract.samples))
    if len(conditions) < 2:
        raise ValueError("Need at least 2 conditions for split violins.")
    cond_left, cond_right = conditions[0], conditions[1]
    left_vals = np.array([s.ratio for s in contract.samples
                          if s.condition == cond_left])
    right_vals = np.array([s.ratio for s in contract.samples
                           if s.condition == cond_right])

    # Split-violin via gaussian KDE.
    from scipy.stats import gaussian_kde
    all_vals = np.concatenate([left_vals, right_vals])
    y_lo = float(min(0.0, all_vals.min() - 0.1))
    y_hi = float(max(contract.threshold * 1.5, all_vals.max() + 0.1))
    y_grid = np.linspace(y_lo, y_hi, 80)

    kde_l = gaussian_kde(left_vals)
    kde_r = gaussian_kde(right_vals)
    d_l = kde_l(y_grid)
    d_r = kde_r(y_grid)
    scale = 0.40 / max(max(d_l.max(), d_r.max()), 1e-6)

    colour_left = _CONDITION_PALETTE.get(cond_left, "#37474F")
    colour_right = _CONDITION_PALETTE.get(cond_right, "#EF5350")

    # Left half (negative x).
    ax.fill_betweenx(y_grid, -d_l * scale, 0,
                     color=colour_left, alpha=0.55, zorder=3)
    ax.plot(-d_l * scale, y_grid, color=colour_left, lw=0.8,
            zorder=4)
    # Right half (positive x).
    ax.fill_betweenx(y_grid, 0, d_r * scale,
                     color=colour_right, alpha=0.55, zorder=3)
    ax.plot(d_r * scale, y_grid, color=colour_right, lw=0.8,
            zorder=4)

    # Per-cell jitter dots.
    rng = np.random.default_rng(708)
    ax.scatter(
        rng.uniform(-0.40, -0.05, left_vals.size),
        left_vals, s=12, color=colour_left, alpha=0.65,
        edgecolor="white", linewidth=0.3, zorder=5,
    )
    ax.scatter(
        rng.uniform(0.05, 0.40, right_vals.size),
        right_vals, s=12, color=colour_right, alpha=0.65,
        edgecolor="white", linewidth=0.3, zorder=5,
    )

    # Median ring markers.
    med_l = float(np.median(left_vals))
    med_r = float(np.median(right_vals))
    ax.scatter([-0.22], [med_l], s=70, marker="o",
               facecolor="white", edgecolor=colour_left,
               linewidth=1.4, zorder=7)
    ax.scatter([0.22], [med_r], s=70, marker="o",
               facecolor="white", edgecolor=colour_right,
               linewidth=1.4, zorder=7)

    # Threshold reference at ratio = 1.0.
    ax.axhline(contract.threshold,
               color="#888888", lw=0.7, ls="--", zorder=2,
               label=f"super-/sub-critical "
                     f"(ratio = {smart_fmt(contract.threshold)})")

    ax.axvline(0, color="#888888", lw=0.4, zorder=2)
    ax.set_xlim(-0.55, 0.55)
    ax.set_ylim(y_lo, y_hi)
    ax.set_xticks([-0.22, 0.22])
    ax.set_xticklabels([cond_left, cond_right], fontsize=7.0)
    ax.set_ylabel("confinement ratio (z-span / Euler L_crit)",
                  fontsize=6.8)
    ax.tick_params(axis="y", labelsize=6.4)
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    # Per-genotype supercritical fraction.
    n_l_super = int((left_vals > contract.threshold).sum())
    n_r_super = int((right_vals > contract.threshold).sum())
    bits = (
        f"{cond_left}: {n_l_super}/{left_vals.size} super  ·  "
        f"{cond_right}: {n_r_super}/{right_vals.size} super"
    )
    ax.legend(fontsize=6.4, frameon=False, loc="upper right",
              handlelength=1.4)
    ax.set_title(
        f"{contract.title}  ·  {bits}",
        fontsize=8.2, pad=4,
    )
    return ax
