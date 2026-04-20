"""Surveillance-efficiency metric forest — condition-level summary with CI.

A composite metric (area surveilled per unit time per cell, in
μm²·min⁻¹·cell⁻¹) per condition, shown as horizontal forest bars with
95 % CI, sorted by estimate. A reference line marks the baseline value
and conditions that cross it in either direction are colour-coded.
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


class SurveillanceEffInput(RecipeContract):
    condition_names: list[str] = Field(..., min_length=2)
    estimate: list[float] = Field(...)
    ci_lo: list[float] = Field(...)
    ci_hi: list[float] = Field(...)
    baseline: float = Field(default=0.0, description="reference baseline")
    metric_label: str = "surveillance (μm²·min⁻¹·cell⁻¹)"
    title: str = "Surveillance efficiency"


def _demo() -> SurveillanceEffInput:
    conditions = ["control", "LPS", "LPS+NAC", "TMEV d3", "IFN-γ", "aged"]
    rng = np.random.default_rng(811)
    est = np.array([24.5, 38.2, 28.7, 42.1, 30.5, 18.3])
    se = rng.uniform(1.6, 3.2, est.size)
    lo = (est - 1.96 * se).tolist()
    hi = (est + 1.96 * se).tolist()
    return SurveillanceEffInput(
        condition_names=conditions,
        estimate=est.tolist(),
        ci_lo=lo,
        ci_hi=hi,
        baseline=24.5,
    )


_META = RecipeMetadata(
    name="surveillance_efficiency_metric",
    modality="intravital_imaging",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "Across conditions, how does the surveillance-efficiency "
        "metric compare, with CI?"
    ),
    required_fields=("condition_names", "estimate", "ci_lo", "ci_hi"),
    optional_fields=("baseline", "metric_label", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("time_to_homing_survival",),
)


@register_recipe(
    metadata=_META,
    contract=SurveillanceEffInput,
    demo_contract=_demo,
)
def render(contract: SurveillanceEffInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.4))
    AESTHETIC.apply_to_ax(ax)

    names = contract.condition_names
    est = np.asarray(contract.estimate, float)
    lo = np.asarray(contract.ci_lo, float)
    hi = np.asarray(contract.ci_hi, float)
    order = np.argsort(-est)
    names = [names[i] for i in order]
    est = est[order]
    lo = lo[order]
    hi = hi[order]

    y = np.arange(len(names))[::-1]
    above_color = "#2E7D32"
    below_color = "#C62828"

    for yi, e, ci_lo, ci_hi in zip(y, est, lo, hi):
        color = above_color if e >= contract.baseline else below_color
        ax.plot([ci_lo, ci_hi], [yi, yi], color=color, lw=1.2, zorder=3)
        for x_end in (ci_lo, ci_hi):
            ax.plot([x_end, x_end], [yi - 0.15, yi + 0.15],
                    color=color, lw=1.2, zorder=3)
        ax.scatter([e], [yi], s=38, color=color,
                   edgecolor="white", linewidth=0.9, zorder=4)

    # Baseline reference (label pinned to lower-right inside axes so it
    # never collides with the title).
    ax.axvline(contract.baseline, color="#555555", lw=0.9, ls="--", zorder=2)
    ax.text(0.98, 0.04,
            f"baseline = {smart_fmt(contract.baseline)}",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6.6, color="#555555",
            bbox=dict(boxstyle="round,pad=0.18", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=5)

    # Numeric labels right-of-CI.
    xhi_ = float(hi.max())
    xlo_ = float(lo.min())
    span = max(xhi_ - xlo_, 1e-6)
    gap = 0.02 * span
    for yi, e, ci_hi in zip(y, est, hi):
        ax.text(ci_hi + gap, yi, smart_fmt(float(e)),
                va="center", ha="left", fontsize=6.8, color="#222222")

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=7.2)
    ax.set_xlabel(contract.metric_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.set_xlim(xlo_ - 0.05 * span, xhi_ + 0.20 * span)

    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
