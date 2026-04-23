"""Calibration plot with Hosmer-Lemeshow test — observed vs predicted
event probability across deciles, reference y=x line, HL χ² / p callout.

Scatter-collapse family: ≥1 scatter + ≥1 line.
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


class CalibrationInput(RecipeContract):
    predicted: list[float] = Field(..., min_length=10,
                                   description="predicted prob per subject")
    observed: list[int] = Field(..., min_length=10,
                                description="observed outcome (0/1)")
    n_bins: int = Field(10, description="deciles by default")
    title: str = "Calibration with Hosmer-Lemeshow"


def _demo() -> CalibrationInput:
    rng = np.random.default_rng(2031)
    n = 800
    # Slightly miscalibrated model: low-risk under-predicts.
    p_true = rng.beta(1.4, 2.5, n)
    p_pred = np.clip(p_true + rng.normal(0, 0.05, n) - 0.03, 0, 1)
    y = (rng.random(n) < p_true).astype(int)
    return CalibrationInput(
        predicted=p_pred.tolist(),
        observed=y.tolist(),
    )


_META = RecipeMetadata(
    name="calibration_plot_with_hl_test",
    modality="clinical_cohort",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Does the predicted probability match the observed outcome "
        "rate across deciles (Hosmer-Lemeshow calibration)?"
    ),
    required_fields=("predicted", "observed"),
    optional_fields=("n_bins", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("roc_with_cutoff_optimization",),
)


@register_recipe(
    metadata=_META, contract=CalibrationInput, demo_contract=_demo,
)
def render(contract: CalibrationInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 4.2))
    AESTHETIC.apply_to_ax(ax)

    p_pred = np.asarray(contract.predicted, float)
    y = np.asarray(contract.observed, int)
    n_bins = int(contract.n_bins)

    # Bin by predicted-probability decile.
    q = np.quantile(p_pred, np.linspace(0, 1, n_bins + 1))
    q[0] -= 1e-9
    q[-1] += 1e-9
    bin_idx = np.digitize(p_pred, q, right=True) - 1
    bin_idx = np.clip(bin_idx, 0, n_bins - 1)

    obs_rate = np.zeros(n_bins)
    pred_rate = np.zeros(n_bins)
    bin_n = np.zeros(n_bins, dtype=int)
    for i in range(n_bins):
        mask = bin_idx == i
        if mask.sum() == 0:
            continue
        obs_rate[i] = y[mask].mean()
        pred_rate[i] = p_pred[mask].mean()
        bin_n[i] = int(mask.sum())

    # Reference diagonal y = x.
    ax.plot([0, 1], [0, 1], color="#888888", lw=0.8, ls="--",
            zorder=2, label="perfect")

    # Point sizes proportional to bin N.
    sizes = 30 + 120 * (bin_n / max(bin_n.max(), 1))
    ax.scatter(pred_rate, obs_rate, s=sizes, color="#1565C0",
               edgecolor="white", linewidth=0.6, alpha=0.9,
               zorder=5, label="deciles")
    # Connecting line for the trend.
    ax.plot(pred_rate, obs_rate, color="#1565C0", lw=1.0,
            alpha=0.45, zorder=4)

    # Hosmer-Lemeshow statistic.
    expected = pred_rate * bin_n
    observed_count = obs_rate * bin_n
    # Avoid division by zero.
    denom = expected * (1 - pred_rate)
    safe = denom > 0
    hl = float(np.sum(
        (observed_count[safe] - expected[safe]) ** 2 / denom[safe]
    ))
    # p-value from chi-square with (n_bins - 2) df.
    from scipy.stats import chi2
    df = max(n_bins - 2, 1)
    hl_p = float(1.0 - chi2.cdf(hl, df))

    ax.set_xlim(0, 1.02)
    ax.set_ylim(0, 1.02)
    ax.set_aspect("equal")
    ax.set_xlabel("predicted probability")
    ax.set_ylabel("observed rate")
    ax.legend(fontsize=6.8, frameon=False, loc="upper left",
              handlelength=1.2)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    if hl_p < 0.05:
        verdict = "poorly calibrated (p < 0.05)"
        color = "#C62828"
    else:
        verdict = f"well calibrated (p = {smart_fmt(hl_p)})"
        color = "#2E7D32"

    ax.set_title(
        f"{contract.title}  ·  HL χ² = {smart_fmt(hl)} "
        f"(df = {df})",
        fontsize=8.4, pad=4,
    )
    ax.text(0.98, 0.02, verdict,
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6.8, color=color,
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=7)
    return ax
