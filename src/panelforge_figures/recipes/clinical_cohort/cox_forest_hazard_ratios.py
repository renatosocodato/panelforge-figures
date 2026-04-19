"""Cox-model forest — hazard ratios with 95% CIs, reference line at HR=1."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    empty_data_guard,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class CoxRow(RecipeContract):
    name: str
    hr: float
    ci_lo: float
    ci_hi: float
    pvalue: float | None = None


class CoxForestInput(RecipeContract):
    covariates: list[CoxRow] = Field(..., min_length=1)
    title: str = "Cox multivariable HRs"


def _demo() -> CoxForestInput:
    return CoxForestInput(
        covariates=[
            CoxRow(name="age (per 10 yr)", hr=1.32, ci_lo=1.15, ci_hi=1.52, pvalue=6e-5),
            CoxRow(name="sex (F vs M)", hr=0.81, ci_lo=0.64, ci_hi=1.03, pvalue=0.09),
            CoxRow(name="stage III vs I-II", hr=2.41, ci_lo=1.68, ci_hi=3.46, pvalue=3e-6),
            CoxRow(name="treatment arm", hr=0.66, ci_lo=0.49, ci_hi=0.89, pvalue=5.2e-3),
            CoxRow(name="comorbidity index", hr=1.14, ci_lo=0.98, ci_hi=1.33, pvalue=0.09),
            CoxRow(name="biomarker +", hr=1.78, ci_lo=1.22, ci_hi=2.58, pvalue=2.4e-3),
        ],
    )


_META = RecipeMetadata(
    name="cox_forest_hazard_ratios",
    modality="clinical_cohort",
    family=RecipeFamily.coef_forest,
    answers_question="Which covariates independently affect hazard, and what is each effect size with its 95% CI?",
    required_fields=("covariates",),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("subgroup_forest_plot",),
)


@register_recipe(metadata=_META, contract=CoxForestInput, demo_contract=_demo)
def render(contract: CoxForestInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.4))
    AESTHETIC.apply_to_ax(ax)
    if empty_data_guard(ax, len(contract.covariates), message="no covariates"):
        return ax
    palette = get_palette(AESTHETIC.primary_palette)

    rows = contract.covariates
    y = np.arange(len(rows))[::-1]
    for yi, r in zip(y, rows):
        color = "#D32F2F" if r.ci_lo > 1 else ("#1565C0" if r.ci_hi < 1 else palette[3])
        ax.plot([r.ci_lo, r.ci_hi], [yi, yi], color=color, lw=1.2, zorder=2)
        for xe in (r.ci_lo, r.ci_hi):
            ax.plot([xe, xe], [yi - 0.18, yi + 0.18], color=color, lw=1.2, zorder=2)
        ax.scatter([r.hr], [yi], s=36, color=color,
                   edgecolor="white", linewidth=0.9, zorder=3)

    ax.axvline(1.0, color="#555555", lw=0.7, ls="--", zorder=1)
    ax.set_xscale("log")
    ax.set_yticks(y)
    ax.set_yticklabels([r.name for r in rows], fontsize=7.2)
    ax.set_xlabel("hazard ratio (log scale, 95% CI)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    # Right-of-CI numeric labels.
    xhi = max(r.ci_hi for r in rows)
    ax.set_xlim(None, xhi * 1.9)
    for yi, r in zip(y, rows):
        p_str = f"  p={smart_fmt(r.pvalue)}" if r.pvalue is not None else ""
        ax.text(r.ci_hi * 1.08, yi,
                f"{smart_fmt(r.hr)} ({smart_fmt(r.ci_lo)}-{smart_fmt(r.ci_hi)}){p_str}",
                va="center", ha="left", fontsize=6.4, color="#222222")

    ax.grid(axis="x", which="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
