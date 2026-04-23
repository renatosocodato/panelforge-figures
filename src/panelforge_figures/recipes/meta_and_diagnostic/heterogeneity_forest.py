"""Heterogeneity forest — per-study ES ± CI with pooled diamond and
I² / τ² / Q callouts.

Coef-forest family: ≥3 markers + ≥1 reference line.
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


class HeterogeneityForestInput(RecipeContract):
    study_names: list[str] = Field(..., min_length=3)
    es: list[float] = Field(..., description="effect size per study")
    ci_lo: list[float] = Field(...)
    ci_hi: list[float] = Field(...)
    weights: list[float] | None = Field(
        None,
        description="per-study weight (for marker size); defaults to 1/SE²",
    )
    pooled_es: float = Field(..., description="pooled effect size")
    pooled_ci_lo: float = Field(...)
    pooled_ci_hi: float = Field(...)
    i_squared: float = Field(..., ge=0.0, le=1.0)
    tau_squared: float = Field(..., ge=0.0)
    q_stat: float | None = None
    title: str = "Heterogeneity forest"


def _demo() -> HeterogeneityForestInput:
    rng = np.random.default_rng(233)
    n = 10
    names = [f"Study {i + 1}" for i in range(n)]
    se = rng.uniform(0.05, 0.25, n)
    es = rng.normal(0.34, 0.18, n)
    ci_lo = es - 1.96 * se
    ci_hi = es + 1.96 * se
    weights = (1.0 / se ** 2).tolist()
    pooled = float(np.average(es, weights=weights))
    pooled_se = float(np.sqrt(1.0 / np.sum(weights)))
    # I² from Q:
    q = float(np.sum((es - pooled) ** 2 * weights))
    df = n - 1
    i2 = max(0.0, (q - df) / max(q, 1e-9))
    tau2 = max((q - df) / max(np.sum(weights) -
                              np.sum(np.array(weights) ** 2) / np.sum(weights), 1e-9),
               0.0)
    return HeterogeneityForestInput(
        study_names=names,
        es=es.tolist(),
        ci_lo=ci_lo.tolist(),
        ci_hi=ci_hi.tolist(),
        weights=weights,
        pooled_es=pooled,
        pooled_ci_lo=pooled - 1.96 * pooled_se,
        pooled_ci_hi=pooled + 1.96 * pooled_se,
        i_squared=i2,
        tau_squared=tau2,
        q_stat=q,
    )


_META = RecipeMetadata(
    name="heterogeneity_forest",
    modality="meta_and_diagnostic",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "Across studies, what is the pooled effect and how "
        "heterogeneous is it (I², τ², Q)?"
    ),
    required_fields=(
        "study_names", "es", "ci_lo", "ci_hi",
        "pooled_es", "pooled_ci_lo", "pooled_ci_hi",
        "i_squared", "tau_squared",
    ),
    optional_fields=("weights", "q_stat", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("sensitivity_leave_one_out",),
)


@register_recipe(
    metadata=_META,
    contract=HeterogeneityForestInput,
    demo_contract=_demo,
)
def render(contract: HeterogeneityForestInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 4.0))
    AESTHETIC.apply_to_ax(ax)

    names = contract.study_names
    es = np.asarray(contract.es, float)
    lo = np.asarray(contract.ci_lo, float)
    hi = np.asarray(contract.ci_hi, float)
    n = len(names)

    # Sort by ES for readability.
    order = np.argsort(es)
    names_s = [names[i] for i in order]
    es_s = es[order]
    lo_s = lo[order]
    hi_s = hi[order]
    if contract.weights is not None:
        w = np.asarray(contract.weights, float)[order]
        sizes = 30 + 120 * (w / max(w.max(), 1e-9))
    else:
        sizes = 60 * np.ones(n)

    y = np.arange(n)
    # Pooled reference line.
    ax.axvline(contract.pooled_es, color="#222222", lw=0.8, zorder=2,
               label=f"pooled = {smart_fmt(float(contract.pooled_es))}")
    # Null line.
    ax.axvline(0.0, color="#888888", lw=0.5, ls="--", zorder=1)

    # Study CI segments.
    for yi, lo_i, hi_i in zip(y, lo_s, hi_s):
        ax.plot([lo_i, hi_i], [yi, yi],
                color="#555555", lw=1.1, zorder=3)
    # Study markers.
    ax.scatter(es_s, y, s=sizes, color="#1565C0",
               edgecolor="white", linewidth=0.6, zorder=5)

    # Pooled diamond at y=-1.
    diamond_y = -1.0
    cx = contract.pooled_es
    lo_p = contract.pooled_ci_lo
    hi_p = contract.pooled_ci_hi
    diamond_x = [lo_p, cx, hi_p, cx, lo_p]
    diamond_yy = [diamond_y, diamond_y + 0.3, diamond_y,
                  diamond_y - 0.3, diamond_y]
    ax.fill(diamond_x, diamond_yy, color="#263238",
            edgecolor="white", linewidth=0.8, zorder=5)
    ax.text(cx, diamond_y - 0.55,
            f"pooled {smart_fmt(cx)}  "
            f"[{smart_fmt(lo_p)}, {smart_fmt(hi_p)}]",
            ha="center", va="top", fontsize=6.8,
            color="#263238", fontweight="bold", zorder=6)

    ax.set_yticks(np.concatenate([[diamond_y], y]))
    ax.set_yticklabels(["Pooled"] + names_s, fontsize=7.0)
    ax.set_ylim(diamond_y - 1.0, n - 0.2)
    ax.set_xlabel("effect size")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="lower right",
              handlelength=1.4)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # I² / τ² / Q callout.
    i2_pct = float(contract.i_squared) * 100
    lines = [
        f"I² = {smart_fmt(i2_pct)} %",
        f"τ² = {smart_fmt(float(contract.tau_squared))}",
    ]
    if contract.q_stat is not None:
        lines.append(f"Q = {smart_fmt(float(contract.q_stat))} (df = {n - 1})")
    ax.text(0.02, 0.97, "\n".join(lines),
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.6, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)
    return ax
