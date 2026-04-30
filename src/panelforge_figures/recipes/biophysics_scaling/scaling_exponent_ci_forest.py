"""Scaling-exponent CI forest — per-study / per-condition α ± CI with
reference line at a theoretical value.

Distinct from `log_log_scaling_with_slope_box` (single α, single
condition). Coef-forest family: ≥3 markers + ≥1 reference line.
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


class ScalingForestInput(RecipeContract):
    study_names: list[str] = Field(..., min_length=3)
    alpha_hat: list[float] = Field(..., description="fitted exponent per study")
    alpha_lo: list[float] = Field(..., description="CI lower")
    alpha_hi: list[float] = Field(..., description="CI upper")
    n_samples: list[int] | None = Field(
        None, description="optional sample size per study (sizes marker)"
    )
    theory_alpha: float | None = Field(None, description="reference vertical line")
    title: str = "Scaling-exponent forest"


def _demo() -> ScalingForestInput:
    rng = np.random.default_rng(599)
    names = [f"study {i+1}" for i in range(10)]
    true_alpha = 1.5
    alpha = rng.normal(true_alpha, 0.14, 10)
    se = rng.uniform(0.06, 0.22, 10)
    n = rng.integers(20, 200, 10).tolist()
    return ScalingForestInput(
        study_names=names,
        alpha_hat=alpha.tolist(),
        alpha_lo=(alpha - 1.96 * se).tolist(),
        alpha_hi=(alpha + 1.96 * se).tolist(),
        n_samples=n,
        theory_alpha=1.5,
        title="Stiffness-length scaling across studies",
    )


_META = RecipeMetadata(
    name="scaling_exponent_ci_forest",
    modality="biophysics_scaling",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "Across studies / conditions, what is the distribution of the "
        "fitted scaling exponent α and its uncertainty?"
    ),
    required_fields=("study_names", "alpha_hat", "alpha_lo", "alpha_hi"),
    optional_fields=("n_samples", "theory_alpha", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("log_log_scaling_with_slope_box",),
)


@register_recipe(
    metadata=_META,
    contract=ScalingForestInput,
    demo_contract=_demo,
)
def render(contract: ScalingForestInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.8))
    AESTHETIC.apply_to_ax(ax)

    names = contract.study_names
    hat = np.asarray(contract.alpha_hat, float)
    lo = np.asarray(contract.alpha_lo, float)
    hi = np.asarray(contract.alpha_hi, float)

    # Sort by α for readability.
    order = np.argsort(hat)
    names_s = [names[i] for i in order]
    hat_s = hat[order]
    lo_s = lo[order]
    hi_s = hi[order]

    y = np.arange(len(names_s))
    sizes = None
    if contract.n_samples is not None:
        ns = np.asarray(contract.n_samples, float)[order]
        sizes = 20 + 80 * (ns / max(ns.max(), 1))
    else:
        sizes = 40 * np.ones(len(y))

    # Theory reference vertical.
    if contract.theory_alpha is not None:
        ax.axvline(contract.theory_alpha, color="#888888", lw=0.8, ls="--",
                   zorder=2,
                   label=f"theory α = {smart_fmt(float(contract.theory_alpha))}")

    # Zero-less baseline (vertical at median).
    median_alpha = float(np.median(hat_s))
    ax.axvline(median_alpha, color="#222222", lw=0.8, zorder=2,
               label=f"median α = {smart_fmt(median_alpha)}")

    # CI segments.
    for yi, lo_i, hi_i in zip(y, lo_s, hi_s):
        ax.plot([lo_i, hi_i], [yi, yi], color="#555555", lw=1.1, zorder=3)

    # Point estimates.
    ax.scatter(hat_s, y, s=sizes, color="#1565C0",
               edgecolor="white", linewidth=0.6, zorder=5)

    ax.set_yticks(y)
    ax.set_yticklabels(names_s, fontsize=7.0)
    ax.set_xlabel(r"scaling exponent α")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="lower right",
              handlelength=1.6)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # I^2-like between-study heterogeneity summary.
    between = float(np.var(hat_s, ddof=1))
    within = float(np.mean(((hi_s - lo_s) / (2 * 1.96)) ** 2))
    heterogeneity = between / max(between + within, 1e-12)
    ax.text(0.02, 0.04,
            f"n = {len(names_s)}  heterogeneity = {smart_fmt(heterogeneity)}",
            transform=ax.transAxes, ha="left", va="bottom",
            fontsize=6.4, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)
    return ax
