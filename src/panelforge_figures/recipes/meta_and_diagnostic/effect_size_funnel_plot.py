"""Effect-size funnel plot — publication-bias diagnostic with 95 %
pseudo-confidence triangular cone and Egger's test p-value callout.
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


class FunnelInput(RecipeContract):
    effect_sizes: list[float] = Field(..., min_length=5,
                                      description="per-study effect size")
    standard_errors: list[float] = Field(..., min_length=5,
                                         description="per-study SE")
    study_names: list[str] | None = None
    pooled_effect: float = Field(...,
                                 description="pooled ES for reference line")
    egger_p: float | None = Field(
        None, description="Egger's test p-value (None = computed below)"
    )
    title: str = "Effect-size funnel plot"


def _demo() -> FunnelInput:
    rng = np.random.default_rng(181)
    # Generate ES + SE; bigger studies (small SE) near pooled, small
    # studies with more variance.
    pooled = 0.35
    se = np.concatenate([
        rng.uniform(0.04, 0.10, 8),
        rng.uniform(0.10, 0.25, 14),
        rng.uniform(0.25, 0.45, 8),
    ])
    es = pooled + rng.normal(0, se * 1.1)
    # Inject a mild publication-bias asymmetry: suppress some negative
    # effects at large SE.
    for i, s in enumerate(se):
        if s > 0.25 and es[i] < pooled - 0.1 and rng.random() < 0.6:
            es[i] = pooled + abs(es[i] - pooled)
    names = [f"S{k+1:02d}" for k in range(len(es))]
    return FunnelInput(
        effect_sizes=es.tolist(),
        standard_errors=se.tolist(),
        study_names=names,
        pooled_effect=float(pooled),
    )


_META = RecipeMetadata(
    name="effect_size_funnel_plot",
    modality="meta_and_diagnostic",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Is there evidence of publication bias in the meta-analysis "
        "(asymmetric funnel plot)?"
    ),
    required_fields=(
        "effect_sizes", "standard_errors", "pooled_effect",
    ),
    optional_fields=("study_names", "egger_p", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("heterogeneity_forest",),
)


@register_recipe(
    metadata=_META,
    contract=FunnelInput,
    demo_contract=_demo,
)
def render(contract: FunnelInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.8))
    AESTHETIC.apply_to_ax(ax)

    es = np.asarray(contract.effect_sizes, float)
    se = np.asarray(contract.standard_errors, float)
    pooled = float(contract.pooled_effect)

    # 95 % pseudo-CI cone: at SE=0 cone tips at pooled; widens as
    # se increases: pooled ± 1.96 * se.
    se_grid = np.linspace(0, float(se.max()) * 1.05, 120)
    lo = pooled - 1.96 * se_grid
    hi = pooled + 1.96 * se_grid
    ax.fill_betweenx(se_grid, lo, hi, color="#BDBDBD",
                     alpha=0.18, linewidth=0, zorder=1,
                     label="95 % cone")
    ax.plot(lo, se_grid, color="#888888", lw=0.6, ls="--", zorder=2)
    ax.plot(hi, se_grid, color="#888888", lw=0.6, ls="--", zorder=2)

    # Pooled effect vertical.
    ax.axvline(pooled, color="#222222", lw=0.8, zorder=3,
               label=f"pooled = {smart_fmt(pooled)}")

    # Study points.
    ax.scatter(es, se, s=36, color="#1565C0", alpha=0.8,
               edgecolor="white", linewidth=0.6, zorder=4,
               label="studies")

    # Egger's regression: z = ES / SE vs precision = 1/SE.
    prec = 1.0 / np.clip(se, 1e-6, None)
    z = es / np.clip(se, 1e-6, None)
    slope, intercept = np.polyfit(prec, z, 1)
    # Approximate Egger p via t-test on intercept.
    n = len(es)
    resid = z - (slope * prec + intercept)
    se_int = np.std(resid, ddof=2) * np.sqrt(
        1 / n + (np.mean(prec) ** 2) / np.sum((prec - prec.mean()) ** 2)
    )
    t_stat = intercept / max(se_int, 1e-9)
    # Two-sided p from normal approximation.
    from scipy.stats import t as tdist
    p_egger = float(2 * (1 - tdist.cdf(abs(t_stat), df=max(n - 2, 1))))
    if contract.egger_p is not None:
        p_egger = float(contract.egger_p)

    verdict = ("asymmetric (possible bias)" if p_egger < 0.1
               else "symmetric (no evidence of bias)")

    ax.set_xlabel("effect size")
    ax.set_ylabel("standard error (SE)")
    ax.invert_yaxis()
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="lower right",
              handlelength=1.2)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    ax.text(0.02, 0.04,
            f"N studies = {n}\n"
            f"Egger intercept = {smart_fmt(float(intercept))}\n"
            f"Egger p = {smart_fmt(p_egger)}\n"
            f"-> {verdict}",
            transform=ax.transAxes, ha="left", va="bottom",
            fontsize=6.4,
            color="#C62828" if p_egger < 0.1 else "#2E7D32",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)
    return ax
