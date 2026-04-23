"""Decision-curve analysis — net benefit vs threshold probability for
the model, treat-all, and treat-none strategies.
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


class DCAInput(RecipeContract):
    thresholds: list[float] = Field(..., min_length=5,
                                    description="threshold probabilities (0..1)")
    net_benefit_model: list[float] = Field(...,
                                           description="model net benefit per threshold")
    net_benefit_treat_all: list[float] = Field(...,
                                               description="treat-all net benefit")
    net_benefit_treat_none: list[float] = Field(...,
                                                description="treat-none (≡ 0) per threshold")
    title: str = "Decision-curve analysis"


def _demo() -> DCAInput:
    rng = np.random.default_rng(2131)
    thr = np.linspace(0.01, 0.6, 80)
    prev = 0.30
    # Treat-all: prev - (1-prev)*(pt/(1-pt))
    ta = prev - (1 - prev) * (thr / np.clip(1 - thr, 1e-6, None))
    tn = np.zeros_like(thr)
    # Model: better than treat-all over moderate thresholds.
    nb_model = np.maximum(ta, 0) + 0.10 * np.exp(-((thr - 0.22) / 0.12) ** 2)
    nb_model = np.maximum(nb_model, tn)
    nb_model += rng.normal(0, 0.006, thr.size)
    return DCAInput(
        thresholds=thr.tolist(),
        net_benefit_model=nb_model.tolist(),
        net_benefit_treat_all=ta.tolist(),
        net_benefit_treat_none=tn.tolist(),
    )


_META = RecipeMetadata(
    name="decision_curve_analysis",
    modality="clinical_cohort",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "Across threshold probabilities, does the model's net benefit "
        "exceed treat-all and treat-none strategies?"
    ),
    required_fields=(
        "thresholds", "net_benefit_model",
        "net_benefit_treat_all", "net_benefit_treat_none",
    ),
    optional_fields=("title",),
    file_format_hints=("csv",),
    alternatives_in_modality=("roc_with_cutoff_optimization",),
)


@register_recipe(metadata=_META, contract=DCAInput, demo_contract=_demo)
def render(contract: DCAInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.8))
    AESTHETIC.apply_to_ax(ax)

    thr = np.asarray(contract.thresholds, float)
    nb_m = np.asarray(contract.net_benefit_model, float)
    nb_a = np.asarray(contract.net_benefit_treat_all, float)
    nb_n = np.asarray(contract.net_benefit_treat_none, float)

    # Fill where model beats both references.
    envelope = np.maximum(nb_a, nb_n)
    ax.fill_between(thr, envelope, nb_m, where=(nb_m > envelope),
                    color="#2E7D32", alpha=0.18, linewidth=0, zorder=2,
                    label="net benefit vs ref")

    ax.plot(thr, nb_a, color="#888888", lw=1.0, ls="--", zorder=3,
            label="treat-all")
    ax.plot(thr, nb_n, color="#444444", lw=1.0, ls=":", zorder=3,
            label="treat-none")
    ax.plot(thr, nb_m, color="#1565C0", lw=1.4, zorder=5,
            label="model")

    # Optimal threshold: where model-benefit over reference is largest.
    over = nb_m - envelope
    best = int(np.argmax(over))
    ax.scatter([thr[best]], [nb_m[best]], s=52, marker="*",
               color="#C62828", edgecolor="white", linewidth=0.9,
               zorder=6)

    ax.axhline(0, color="#BBBBBB", lw=0.5, zorder=1)
    ax.set_xlabel("threshold probability")
    ax.set_ylabel("net benefit")
    ax.set_xlim(thr.min(), thr.max())
    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              handlelength=1.4)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Range of thresholds where model dominates.
    dominant_mask = nb_m > envelope
    if dominant_mask.any():
        dom_lo = float(thr[dominant_mask].min())
        dom_hi = float(thr[dominant_mask].max())
        dom_txt = (f"model dominates [{smart_fmt(dom_lo)}, "
                   f"{smart_fmt(dom_hi)}]")
        verdict_color = "#2E7D32"
    else:
        dom_txt = "model never dominates"
        verdict_color = "#C62828"

    ax.set_title(
        f"{contract.title}  ·  best threshold = "
        f"{smart_fmt(float(thr[best]))}",
        fontsize=8.6, pad=4,
    )
    ax.text(0.02, 0.04, dom_txt,
            transform=ax.transAxes, ha="left", va="bottom",
            fontsize=6.4, color=verdict_color,
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=7)
    return ax
