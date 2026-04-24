"""Risk-score discrimination ladder — event rate per risk-score
tertile / decile with monotonicity trend line and p-for-trend.

Distinct from `outcome_by_quartile` (exposure quartile → outcome);
here the tiers are **risk-score** tertiles/deciles and the question
is model-discrimination.
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


class RiskScoreLadderInput(RecipeContract):
    tier_names: list[str] = Field(..., min_length=3)
    event_rate: list[float] = Field(...,
                                    description="event rate per tier, [0, 1]")
    ci_lo: list[float] = Field(...)
    ci_hi: list[float] = Field(...)
    n_per_tier: list[int] = Field(..., description="cohort size per tier")
    p_for_trend: float | None = Field(
        None, description="Cochran-Armitage / Mantel-Haenszel trend p"
    )
    title: str = "Risk-score discrimination"


def _demo() -> RiskScoreLadderInput:
    rng = np.random.default_rng(2301)
    names = ["low (T1)", "mid (T2)", "high (T3)", "very-high (T4)"]
    true_rates = [0.04, 0.10, 0.21, 0.38]
    rates = [float(r + rng.normal(0, 0.005)) for r in true_rates]
    n = [320, 310, 295, 280]
    se = [float(np.sqrt(r * (1 - r) / ni)) for r, ni in zip(rates, n)]
    return RiskScoreLadderInput(
        tier_names=names,
        event_rate=rates,
        ci_lo=[max(r - 1.96 * s, 0.0) for r, s in zip(rates, se)],
        ci_hi=[min(r + 1.96 * s, 1.0) for r, s in zip(rates, se)],
        n_per_tier=n,
        p_for_trend=2e-8,
    )


_META = RecipeMetadata(
    name="risk_score_discrimination_ladder",
    modality="clinical_cohort",
    family=RecipeFamily.ladder,
    answers_question=(
        "Across risk-score tertiles / deciles, does the event rate "
        "increase monotonically with the score?"
    ),
    required_fields=(
        "tier_names", "event_rate", "ci_lo", "ci_hi", "n_per_tier",
    ),
    optional_fields=("p_for_trend", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("outcome_by_quartile",),
)


@register_recipe(
    metadata=_META,
    contract=RiskScoreLadderInput,
    demo_contract=_demo,
)
def render(contract: RiskScoreLadderInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.4))
    AESTHETIC.apply_to_ax(ax)

    names = contract.tier_names
    rates = np.asarray(contract.event_rate, float)
    lo = np.asarray(contract.ci_lo, float)
    hi = np.asarray(contract.ci_hi, float)
    n = np.asarray(contract.n_per_tier, int)
    k = len(names)
    x = np.arange(k)

    # Gradient colour from pale to saturated to reinforce monotonicity.
    gradient = ["#BBDEFB", "#64B5F6", "#1E88E5", "#0D47A1",
                "#08306B"]
    bar_colors = [gradient[min(i, len(gradient) - 1)] for i in range(k)]

    # Bars.
    ax.bar(x, rates, color=bar_colors, edgecolor="white", linewidth=0.7,
           alpha=0.92, zorder=3, width=0.7)
    # CI whiskers.
    for xi, r, lo_i, hi_i in zip(x, rates, lo, hi):
        ax.plot([xi, xi], [lo_i, hi_i], color="#333333", lw=1.0,
                zorder=4)
    # Per-bar rate + n labels on top.
    for xi, r, ni in zip(x, rates, n):
        ax.text(xi, r + (hi.max() - lo.min()) * 0.02 + 0.005,
                f"{r:.1%}\nn = {ni}",
                ha="center", va="bottom", fontsize=6.6,
                color="#222222", zorder=5)

    # Trend line across bar heights.
    slope, intercept = np.polyfit(x, rates, 1)
    xfit = np.linspace(-0.3, k - 0.7, 40)
    ax.plot(xfit, slope * xfit + intercept,
            color="#C62828", lw=1.0, ls="--", zorder=4,
            label="trend")

    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=7.0)
    ax.set_ylabel("event rate")
    ax.set_xlabel("risk-score tier")
    ax.set_ylim(0, hi.max() * 1.35)
    ax.legend(fontsize=6.8, frameon=False, loc="upper left",
              handlelength=1.2)
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    # Monotonicity + trend p callouts baked into title.
    monotone = bool(np.all(np.diff(rates) > 0))
    mono_txt = "monotonic ↑" if monotone else "non-monotonic"
    if contract.p_for_trend is not None:
        p_txt = f"p-for-trend = {smart_fmt(float(contract.p_for_trend))}"
    else:
        p_txt = f"slope = {smart_fmt(float(slope))}/tier"
    ax.set_title(
        f"{contract.title}  ·  {mono_txt}  ·  {p_txt}".replace("↑", "up"),
        fontsize=8.4, pad=4,
    )
    return ax
