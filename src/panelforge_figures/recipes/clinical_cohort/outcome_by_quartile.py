"""Outcome by exposure quartile — event rate + 95% CI across quartiles."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class OutcomeQuartileInput(RecipeContract):
    quartile_labels: list[str] = Field(..., min_length=2)
    n_per_quartile: list[int]
    event_rate: list[float] = Field(..., description="cumulative event rate per quartile")
    ci_lo: list[float]
    ci_hi: list[float]
    trend_pvalue: float | None = None
    title: str = "Outcome by exposure quartile"


def _demo() -> OutcomeQuartileInput:
    rng = np.random.default_rng(431)
    labels = ["Q1 (lowest)", "Q2", "Q3", "Q4 (highest)"]
    n = [132, 129, 134, 130]
    er = np.array([0.14, 0.22, 0.31, 0.46]) + rng.normal(0, 0.005, 4)
    se = np.sqrt(er * (1 - er) / np.array(n))
    return OutcomeQuartileInput(
        quartile_labels=labels,
        n_per_quartile=n,
        event_rate=er.tolist(),
        ci_lo=(er - 1.96 * se).tolist(),
        ci_hi=(er + 1.96 * se).tolist(),
        trend_pvalue=3.4e-7,
    )


_META = RecipeMetadata(
    name="outcome_by_quartile",
    modality="clinical_cohort",
    family=RecipeFamily.ladder,
    answers_question="Does the outcome rate increase monotonically across quartiles of the exposure, with a significant trend?",
    required_fields=("quartile_labels", "n_per_quartile", "event_rate", "ci_lo", "ci_hi"),
    optional_fields=("trend_pvalue", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("cox_forest_hazard_ratios",),
)


@register_recipe(metadata=_META, contract=OutcomeQuartileInput, demo_contract=_demo)
def render(contract: OutcomeQuartileInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    labels = contract.quartile_labels
    n = contract.n_per_quartile
    er = np.array(contract.event_rate, dtype=float)
    lo = np.array(contract.ci_lo, dtype=float)
    hi = np.array(contract.ci_hi, dtype=float)
    x = np.arange(len(labels))

    ax.bar(x, er, color=palette[1], alpha=0.82, edgecolor="white",
           linewidth=0.6, zorder=2, width=0.72)
    # Error bars.
    ax.vlines(x, lo, hi, color="#333333", lw=0.9, zorder=3)
    for xi, val in zip(x, er):
        ax.text(xi, val + 0.01, f"{val * 100:.0f}%",
                ha="center", va="bottom", fontsize=6.6, color="#222222")

    # Trend line.
    slope, intercept = np.polyfit(x, er, 1)
    ax.plot(x, slope * x + intercept, color="#D32F2F", lw=1.3,
            ls="--", zorder=4, label=f"trend (slope={smart_fmt(float(slope))})")

    ax.set_xticks(x)
    ax.set_xticklabels([f"{lab}\n(n={ni})" for lab, ni in zip(labels, n)],
                       fontsize=6.8)
    ax.set_ylabel("event rate")
    ax.set_ylim(0, max(hi.max() * 1.25, 0.5))

    title = contract.title
    if contract.trend_pvalue is not None:
        title = f"{title}  ·  trend p = {smart_fmt(contract.trend_pvalue)}"
    ax.set_title(title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="upper left", handlelength=1.6)
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
