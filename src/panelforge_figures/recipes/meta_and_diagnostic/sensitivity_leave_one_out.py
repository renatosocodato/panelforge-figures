"""Leave-one-out sensitivity forest — per-row pooled ES computed
WITHOUT that study, with original pooled line for comparison.

Coef-forest family.
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


class LOOInput(RecipeContract):
    study_names: list[str] = Field(..., min_length=3)
    loo_pooled_es: list[float] = Field(
        ..., description="pooled ES with study k removed, per k"
    )
    loo_ci_lo: list[float] = Field(...)
    loo_ci_hi: list[float] = Field(...)
    original_pooled_es: float = Field(...)
    original_pooled_ci_lo: float = Field(...)
    original_pooled_ci_hi: float = Field(...)
    title: str = "Leave-one-out sensitivity"


def _demo() -> LOOInput:
    rng = np.random.default_rng(317)
    n = 10
    names = [f"Study {i + 1}" for i in range(n)]
    # Original pooled.
    orig = 0.34
    orig_se = 0.04
    # LOO estimates cluster tightly around orig with small perturbations;
    # one "influential" study shifts the pooled.
    loo = orig + rng.normal(0, 0.02, n)
    loo[3] = orig + 0.12   # influential study
    se = rng.uniform(0.03, 0.06, n)
    ci_lo = loo - 1.96 * se
    ci_hi = loo + 1.96 * se
    return LOOInput(
        study_names=names,
        loo_pooled_es=loo.tolist(),
        loo_ci_lo=ci_lo.tolist(),
        loo_ci_hi=ci_hi.tolist(),
        original_pooled_es=orig,
        original_pooled_ci_lo=orig - 1.96 * orig_se,
        original_pooled_ci_hi=orig + 1.96 * orig_se,
    )


_META = RecipeMetadata(
    name="sensitivity_leave_one_out",
    modality="meta_and_diagnostic",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "Does any single study drive the pooled effect (leave-one-out "
        "sensitivity analysis)?"
    ),
    required_fields=(
        "study_names", "loo_pooled_es", "loo_ci_lo", "loo_ci_hi",
        "original_pooled_es",
        "original_pooled_ci_lo", "original_pooled_ci_hi",
    ),
    optional_fields=("title",),
    file_format_hints=("csv",),
    alternatives_in_modality=("heterogeneity_forest",),
)


@register_recipe(
    metadata=_META,
    contract=LOOInput,
    demo_contract=_demo,
)
def render(contract: LOOInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.8))
    AESTHETIC.apply_to_ax(ax)

    names = contract.study_names
    loo = np.asarray(contract.loo_pooled_es, float)
    lo = np.asarray(contract.loo_ci_lo, float)
    hi = np.asarray(contract.loo_ci_hi, float)
    orig = float(contract.original_pooled_es)
    orig_lo = float(contract.original_pooled_ci_lo)
    orig_hi = float(contract.original_pooled_ci_hi)

    # Compute deviation from original pooled.
    dev = loo - orig
    # Flag influential studies as |dev| > 0.05 (or other threshold).
    threshold = max(0.5 * np.std(dev, ddof=1), 0.02)
    flagged = np.abs(dev) > threshold

    # Sort rows by LOO ES ascending (optional — keep original order
    # to mirror the user's study ordering).
    y = np.arange(len(names))

    # Original pooled band.
    ax.axvspan(orig_lo, orig_hi, color="#BBBBBB", alpha=0.20,
               linewidth=0, zorder=1,
               label=f"original pooled 95 % CI")
    ax.axvline(orig, color="#222222", lw=0.8, zorder=2,
               label=f"original pooled = {smart_fmt(orig)}")

    # LOO CI segments.
    for yi, lo_i, hi_i in zip(y, lo, hi):
        ax.plot([lo_i, hi_i], [yi, yi],
                color="#555555", lw=1.0, zorder=3)

    # LOO markers — color flagged studies red.
    colors = np.where(flagged, "#C62828", "#1565C0")
    for yi, pt, c in zip(y, loo, colors):
        ax.scatter([pt], [yi], s=46, color=c,
                   edgecolor="white", linewidth=0.6, zorder=5)

    # Annotate flagged.
    for yi, (nm, d, pt, flag) in enumerate(zip(names, dev, loo, flagged)):
        if flag:
            ax.text(pt + 0.015, yi, f"Δ = {smart_fmt(float(d))}",
                    ha="left", va="center", fontsize=6.4,
                    color="#C62828", zorder=6)

    ax.set_yticks(y)
    ax.set_yticklabels([f"w/o {n}" for n in names], fontsize=6.8)
    ax.set_xlabel("pooled effect size (study removed)")
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.8, frameon=False, loc="lower right",
              handlelength=1.2)

    # Bake N + flag summary into the title so it doesn't occlude any
    # row marker at the bottom of the forest.
    n_flag = int(flagged.sum())
    ax.set_title(
        f"{contract.title}  ·  N = {len(names)}   "
        f"flagged (|Δ| > {smart_fmt(threshold)}) = {n_flag}",
        fontsize=8.4, pad=4,
    )
    return ax
