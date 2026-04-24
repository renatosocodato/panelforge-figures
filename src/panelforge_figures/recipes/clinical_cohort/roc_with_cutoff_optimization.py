"""ROC curve with Youden-index cutoff optimisation — sensitivity vs
(1 − specificity) with AUC + Youden-best cutoff callout.
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


class ROCInput(RecipeContract):
    fpr: list[float] = Field(..., min_length=3,
                             description="false-positive rate (1 - spec) at each cutoff")
    tpr: list[float] = Field(..., min_length=3,
                             description="true-positive rate (sens) at each cutoff")
    cutoffs: list[float] = Field(..., min_length=3,
                                 description="underlying score cutoffs")
    auc: float = Field(..., ge=0.0, le=1.0)
    auc_ci_lo: float | None = None
    auc_ci_hi: float | None = None
    title: str = "ROC — Youden-optimised cutoff"


def _demo() -> ROCInput:
    rng = np.random.default_rng(1901)
    # Simulate a good biomarker via logistic scores.
    n = 400
    labels = rng.integers(0, 2, n)
    scores = rng.normal(labels * 1.2, 1.0, n)
    thresh = np.linspace(scores.min(), scores.max(), 120)
    tpr, fpr = [], []
    for t in thresh[::-1]:   # descending thresh so fpr goes 0 → 1
        pred = scores >= t
        tp = int(np.sum(pred & (labels == 1)))
        fn = int(np.sum(~pred & (labels == 1)))
        fp = int(np.sum(pred & (labels == 0)))
        tn = int(np.sum(~pred & (labels == 0)))
        tpr.append(tp / max(tp + fn, 1))
        fpr.append(fp / max(fp + tn, 1))
    tpr = np.asarray(tpr)
    fpr = np.asarray(fpr)
    # AUC via trapezoid.
    order = np.argsort(fpr)
    auc = float(np.trapezoid(tpr[order], fpr[order]))
    # Bootstrap CI.
    boot_aucs = []
    for _ in range(200):
        idx = rng.integers(0, n, n)
        y = labels[idx]
        s = scores[idx]
        t_boot = []
        f_boot = []
        for t in thresh[::-1]:
            pred = s >= t
            tp = int(np.sum(pred & (y == 1)))
            fn = int(np.sum(~pred & (y == 1)))
            fp = int(np.sum(pred & (y == 0)))
            tn = int(np.sum(~pred & (y == 0)))
            t_boot.append(tp / max(tp + fn, 1))
            f_boot.append(fp / max(fp + tn, 1))
        t_arr = np.asarray(t_boot)
        f_arr = np.asarray(f_boot)
        o = np.argsort(f_arr)
        boot_aucs.append(float(np.trapezoid(t_arr[o], f_arr[o])))
    auc_lo = float(np.percentile(boot_aucs, 2.5))
    auc_hi = float(np.percentile(boot_aucs, 97.5))
    return ROCInput(
        fpr=fpr.tolist(),
        tpr=tpr.tolist(),
        cutoffs=thresh[::-1].tolist(),
        auc=auc,
        auc_ci_lo=auc_lo,
        auc_ci_hi=auc_hi,
    )


_META = RecipeMetadata(
    name="roc_with_cutoff_optimization",
    modality="clinical_cohort",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "At what cutoff does the biomarker maximise sensitivity + "
        "specificity (Youden index), and what is the AUC?"
    ),
    required_fields=("fpr", "tpr", "cutoffs", "auc"),
    optional_fields=("auc_ci_lo", "auc_ci_hi", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("calibration_plot_with_hl_test",),
)


@register_recipe(metadata=_META, contract=ROCInput, demo_contract=_demo)
def render(contract: ROCInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 4.0))
    AESTHETIC.apply_to_ax(ax)

    fpr = np.asarray(contract.fpr, float)
    tpr = np.asarray(contract.tpr, float)
    cutoffs = np.asarray(contract.cutoffs, float)

    # ROC curve + reference diagonal.
    ax.plot([0, 1], [0, 1], color="#888888", lw=0.8, ls="--",
            zorder=2, label="chance")
    ax.plot(fpr, tpr, color="#1565C0", lw=1.4, zorder=4,
            label=f"ROC  AUC = {smart_fmt(float(contract.auc))}")

    # Youden J = tpr - fpr.
    J = tpr - fpr
    best = int(np.argmax(J))
    ax.scatter([fpr[best]], [tpr[best]], s=62, marker="*",
               color="#C62828", edgecolor="white", linewidth=0.9,
               zorder=6,
               label=(f"Youden @ c = {smart_fmt(float(cutoffs[best]))} "
                      f"(J = {smart_fmt(float(J[best]))})"))

    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlabel("1 − specificity (FPR)")
    ax.set_ylabel("sensitivity (TPR)")
    ax.set_aspect("equal")
    ax.legend(fontsize=6.8, frameon=False, loc="lower right",
              handlelength=1.4)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # AUC CI callout.
    if contract.auc_ci_lo is not None and contract.auc_ci_hi is not None:
        ci_txt = (f"AUC = {smart_fmt(float(contract.auc))} "
                  f"[{smart_fmt(float(contract.auc_ci_lo))}, "
                  f"{smart_fmt(float(contract.auc_ci_hi))}]")
    else:
        ci_txt = f"AUC = {smart_fmt(float(contract.auc))}"
    ax.set_title(
        f"{contract.title}  ·  {ci_txt}",
        fontsize=8.6, pad=4,
    )

    # Sensitivity / specificity at best cutoff.
    sens = float(tpr[best])
    spec = 1.0 - float(fpr[best])
    ax.text(0.02, 0.97,
            f"best cutoff c = {smart_fmt(float(cutoffs[best]))}\n"
            f"sens = {smart_fmt(sens)}   spec = {smart_fmt(spec)}",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.4, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=7)
    return ax
