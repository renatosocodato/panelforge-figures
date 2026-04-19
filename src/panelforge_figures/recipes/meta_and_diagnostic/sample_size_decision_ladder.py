"""Decision ladder: required N vs. effect size, annotated with budget lines.

Rendered as a stepped ladder with effect-size tiers on y and required N on x.
Shaded regions highlight the "tractable" and "unreachable" zones given the
funded budget ceiling.
"""

from __future__ import annotations

import matplotlib.patches as mpatches
import numpy as np
from pydantic import Field
from scipy import stats

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class SampleSizeLadderInput(RecipeContract):
    effect_sizes: list[float] = Field(..., description="d tiers in decreasing order of d")
    power: float = 0.80
    alpha: float = 0.05
    budget_n: int | None = Field(None, description="Max feasible N per group")
    effect_labels: list[str] | None = None
    title: str = "Required N for 80% power"


def _demo() -> SampleSizeLadderInput:
    return SampleSizeLadderInput(
        effect_sizes=[1.2, 0.8, 0.5, 0.3, 0.2, 0.1],
        power=0.80,
        alpha=0.05,
        budget_n=90,
        effect_labels=["very large", "large", "medium", "small-med", "small", "tiny"],
    )


def _required_n(d: float, power: float, alpha: float) -> int:
    """Smallest n/group reaching `power` for d via analytical t-test."""
    for n in range(4, 5000):
        df = 2 * n - 2
        nc = d * np.sqrt(n / 2.0)
        crit = stats.t.ppf(1 - alpha / 2, df)
        p = 1 - stats.nct.cdf(crit, df=df, nc=nc) + stats.nct.cdf(-crit, df=df, nc=nc)
        if p >= power:
            return n
    return 5000


_META = RecipeMetadata(
    name="sample_size_decision_ladder",
    modality="meta_and_diagnostic",
    family=RecipeFamily.ladder,
    answers_question="For each candidate effect size tier, what sample size do we need, and what does the budget allow?",
    required_fields=("effect_sizes",),
    optional_fields=("power", "alpha", "budget_n", "effect_labels", "title"),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("power_analysis_by_effect_size",),
)


@register_recipe(metadata=_META, contract=SampleSizeLadderInput, demo_contract=_demo)
def render(contract: SampleSizeLadderInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)
    ds = list(contract.effect_sizes)
    labels = contract.effect_labels or [smart_fmt(d) for d in ds]
    ns = [_required_n(d, contract.power, contract.alpha) for d in ds]

    # Bar per tier — colored by tractability. Use ytick labels so matplotlib
    # budgets room for the d-tier text automatically (avoids overlap at small
    # axis widths).
    ypos = np.arange(len(ds))
    xmax_hint = max(max(ns) * 1.18, (contract.budget_n or 0) * 1.2)
    for y, d, lbl, n in zip(ypos, ds, labels, ns):
        tractable = contract.budget_n is None or n <= contract.budget_n
        color = palette[0] if tractable else "#C62828"
        ax.barh(y, n, height=0.6, color=color, alpha=0.85, edgecolor="white",
                linewidth=0.8, zorder=2)
        # Right-of-bar n= label, with a small gap scaled to axis width.
        ax.text(n + xmax_hint * 0.012, y, f"n={n}", va="center", ha="left",
                fontsize=7.0, color=color)
    ytick_labels = [f"d = {smart_fmt(d)}  ·  {lbl}"
                    for d, lbl in zip(ds, labels)]

    # Budget line + shaded "reach" regions.
    if contract.budget_n is not None:
        ax.axvline(contract.budget_n, color="#D32F2F", lw=1.2, ls="--", zorder=3)
        # Budget label anchored in axes fraction so it never crowds bar labels.
        ax.annotate(
            f"budget n={contract.budget_n}",
            xy=(contract.budget_n, 1.015),
            xycoords=("data", "axes fraction"),
            ha="center", va="bottom", fontsize=7.0, color="#D32F2F",
            bbox=dict(boxstyle="round,pad=0.16", fc="white",
                      ec="none", alpha=0.92),
        )
        ax.add_patch(mpatches.Rectangle(
            (0, -0.5), contract.budget_n, len(ds),
            facecolor="#E8F5E9", alpha=0.35, zorder=0,
        ))
        ax.add_patch(mpatches.Rectangle(
            (contract.budget_n, -0.5), xmax_hint - contract.budget_n, len(ds),
            facecolor="#FFEBEE", alpha=0.35, zorder=0,
        ))

    ax.set_yticks(ypos)
    ax.set_yticklabels(ytick_labels, fontsize=7.0)
    ax.invert_yaxis()
    ax.set_ylim(len(ds) - 0.5, -1.6)
    xmax = xmax_hint
    ax.set_xlim(0, xmax)
    ax.set_xlabel("Required n per group")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.grid(axis="x", color="#DDDDDD", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
