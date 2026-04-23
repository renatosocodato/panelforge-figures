"""Time-varying hazard ratio — smoothed HR(t) with 95 % band and
HR=1 reference line, used as a proportional-hazards (PH) diagnostic.
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


class HRTimeInput(RecipeContract):
    time_points: list[float] = Field(..., min_length=5)
    hr_t: list[float] = Field(..., description="HR(t) point estimate")
    hr_lo: list[float] = Field(..., description="HR(t) 95 % CI lower")
    hr_hi: list[float] = Field(..., description="HR(t) 95 % CI upper")
    ph_test_p: float | None = Field(
        None, description="Schoenfeld residual PH test p-value"
    )
    title: str = "Time-varying hazard ratio"


def _demo() -> HRTimeInput:
    rng = np.random.default_rng(2211)
    t = np.linspace(0, 36, 80)
    # HR starts near 0.6 (early protective), drifts to 1.0 later →
    # PH violation.
    hr = 0.6 + 0.5 * (1 - np.exp(-(t / 18)))
    hr += rng.normal(0, 0.03, t.size)
    se = 0.08 + 0.006 * t
    return HRTimeInput(
        time_points=t.tolist(),
        hr_t=hr.tolist(),
        hr_lo=(hr - 1.96 * se).tolist(),
        hr_hi=(hr + 1.96 * se).tolist(),
        ph_test_p=0.004,
    )


_META = RecipeMetadata(
    name="hazard_ratio_over_time_smoothed",
    modality="clinical_cohort",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "Does the hazard ratio between arms change over follow-up "
        "(proportional-hazards diagnostic)?"
    ),
    required_fields=("time_points", "hr_t", "hr_lo", "hr_hi"),
    optional_fields=("ph_test_p", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("cox_forest_hazard_ratios",),
)


@register_recipe(
    metadata=_META, contract=HRTimeInput, demo_contract=_demo,
)
def render(contract: HRTimeInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.6))
    AESTHETIC.apply_to_ax(ax)

    t = np.asarray(contract.time_points, float)
    hr = np.asarray(contract.hr_t, float)
    lo = np.asarray(contract.hr_lo, float)
    hi = np.asarray(contract.hr_hi, float)

    # HR=1 reference.
    ax.axhline(1.0, color="#888888", lw=0.8, ls="--", zorder=2,
               label="HR = 1 (no effect)")
    # CI band.
    ax.fill_between(t, np.maximum(lo, 0.01), hi,
                    color="#1565C0", alpha=0.20, linewidth=0,
                    zorder=3, label="95 % CI")
    # Point estimate.
    ax.plot(t, hr, color="#0D47A1", lw=1.4, zorder=5,
            label="HR(t)")

    ax.set_yscale("log")
    ax.set_xlabel("follow-up time")
    ax.set_ylabel("hazard ratio")
    ax.set_xlim(t.min(), t.max())
    ax.legend(fontsize=6.8, frameon=False, loc="upper left",
              handlelength=1.4)
    ax.grid(axis="both", which="both", color="#EEEEEE", lw=0.4,
            zorder=0)
    ax.set_axisbelow(True)

    # PH-test verdict.
    if contract.ph_test_p is not None:
        p = float(contract.ph_test_p)
        if p < 0.05:
            verdict = f"PH violated (p = {smart_fmt(p)})"
            color = "#C62828"
        else:
            verdict = f"PH holds (p = {smart_fmt(p)})"
            color = "#2E7D32"
        ax.set_title(
            f"{contract.title}  ·  Schoenfeld p = {smart_fmt(p)}  "
            f"· {verdict}",
            fontsize=8.2, pad=4,
        )
    else:
        ax.set_title(contract.title, fontsize=9.0, pad=4)

    # Summary: early vs late HR.
    n = len(t)
    early_hr = float(np.mean(hr[:max(n // 4, 1)]))
    late_hr = float(np.mean(hr[-max(n // 4, 1):]))
    ax.text(0.98, 0.04,
            f"early HR ≈ {smart_fmt(early_hr)}   "
            f"late HR ≈ {smart_fmt(late_hr)}",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6.4, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=7)
    return ax
