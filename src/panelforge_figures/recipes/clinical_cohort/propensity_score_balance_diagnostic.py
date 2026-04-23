"""Propensity-score balance diagnostic — paired SMD forest showing
covariate imbalance BEFORE vs AFTER matching / IPTW, with SMD=0.1
reference band.

Distinct from `baseline_table_visualization` (single unadjusted SMD
table): here we see the effect of the causal-inference adjustment.
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


class BalanceRow(RecipeContract):
    covariate: str
    smd_before: float
    smd_after: float


class PSBalanceInput(RecipeContract):
    rows: list[BalanceRow] = Field(..., min_length=3)
    threshold: float = Field(
        0.10, description="absolute-SMD balance threshold (default 0.10)"
    )
    title: str = "Propensity-score balance"


def _demo() -> PSBalanceInput:
    rng = np.random.default_rng(2511)
    covs = ["age", "sex", "BMI", "smoking", "diabetes",
            "hypertension", "prior CVD", "LDL cholesterol",
            "HbA1c", "eGFR", "region"]
    # BEFORE: several covariates imbalanced (|SMD| > 0.1).
    before = rng.uniform(-0.45, 0.45, len(covs))
    # AFTER: most pulled inside the threshold.
    after = before * rng.uniform(0.05, 0.30, len(covs))
    rows = [BalanceRow(covariate=c,
                       smd_before=float(b),
                       smd_after=float(a))
            for c, b, a in zip(covs, before, after)]
    return PSBalanceInput(rows=rows)


_META = RecipeMetadata(
    name="propensity_score_balance_diagnostic",
    modality="clinical_cohort",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "After propensity-score matching / IPTW, are baseline "
        "covariates balanced (|SMD| < 0.1)?"
    ),
    required_fields=("rows",),
    optional_fields=("threshold", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("baseline_table_visualization",),
)


@register_recipe(
    metadata=_META, contract=PSBalanceInput, demo_contract=_demo,
)
def render(contract: PSBalanceInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 4.0))
    AESTHETIC.apply_to_ax(ax)

    rows = list(contract.rows)
    names = [r.covariate for r in rows]
    before = np.asarray([r.smd_before for r in rows], float)
    after = np.asarray([r.smd_after for r in rows], float)
    thr = float(contract.threshold)

    # Sort by |before| descending so worst imbalance is at top.
    order = np.argsort(-np.abs(before))
    names_s = [names[i] for i in order]
    before_s = before[order]
    after_s = after[order]
    y = np.arange(len(names_s))

    # Balance band.
    ax.axvspan(-thr, thr, color="#2E7D32", alpha=0.12, linewidth=0,
               zorder=1, label=f"|SMD| ≤ {thr}".replace("≤", "<="))
    ax.axvline(0.0, color="#222222", lw=0.6, zorder=2)

    # Connecting arrow from BEFORE to AFTER per row.
    for yi, b, a in zip(y, before_s, after_s):
        ax.annotate(
            "", xy=(a, yi), xytext=(b, yi),
            arrowprops=dict(arrowstyle="->", color="#777777",
                            lw=0.8, mutation_scale=10,
                            shrinkA=3, shrinkB=3),
            zorder=3,
        )
    # Markers.
    ax.scatter(before_s, y, s=46, marker="o",
               color="#BDBDBD", edgecolor="white", linewidth=0.6,
               zorder=4, label="before")
    ax.scatter(after_s, y, s=46, marker="s",
               color="#1565C0", edgecolor="white", linewidth=0.6,
               zorder=5, label="after")

    ax.set_yticks(y)
    ax.set_yticklabels(names_s, fontsize=6.8)
    ax.set_xlabel("standardised mean difference (SMD)")
    # Legend below the axes so it cannot hide the bottom forest rows
    # (the rows with positive before-SMD typically sit at the bottom
    # of the sort).
    ax.legend(fontsize=6.8, frameon=False, loc="upper center",
              bbox_to_anchor=(0.5, -0.18),
              handlelength=1.2, ncols=3, columnspacing=1.4)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Balance summary.
    n_before_bad = int(np.sum(np.abs(before_s) > thr))
    n_after_bad = int(np.sum(np.abs(after_s) > thr))
    verdict_color = "#2E7D32" if n_after_bad == 0 else "#F57C00"
    ax.set_title(
        f"{contract.title}  ·  imbalanced (|SMD| > {thr}): "
        f"{n_before_bad} before -> {n_after_bad} after",
        fontsize=8.2, pad=4,
        color=verdict_color,
    )
    return ax
