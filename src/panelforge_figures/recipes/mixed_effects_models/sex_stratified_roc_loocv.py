"""Sex-stratified ROC with LOOCV — per-stratum classifier ROC curves
with leave-one-out cross-validation, AUC + 95% CI in legend.

Renders one ROC curve per sex stratum (or any orthogonal stratum
labels) with the diagonal chance reference line. Each curve is
drawn from per-LOO-fold (1-specificity, sensitivity) points + a
smoothed (LOO-monotonised) curve as the fit line.

Scatter-collapse family: >=1 scatter + >=1 fit line. Satisfied by
the per-fold scatter points + the diagonal chance line + per-stratum
smooth ROC fit.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    StatisticalContract,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC
from ._shared import LOOCVAUCEntry


class SexStratifiedROCInput(RecipeContract):
    entries: list[LOOCVAUCEntry] = Field(..., min_length=2)
    title: str = "Sex-stratified ROC (LOOCV)"


def _demo() -> SexStratifiedROCInput:
    rng = np.random.default_rng(821)

    def _make_roc(target_auc: float, n_fpr: int = 25, jitter: float = 0.05):
        """Synthesise a (FPR, TPR) curve at approximately the target AUC."""
        fpr = np.linspace(0.0, 1.0, n_fpr)
        # Power curve TPR = FPR**(1-AUC*alpha) tuned via numeric search.
        # Quick approx: use TPR = 1 - (1 - FPR)**k with k chosen by
        # AUC = 1 - 1/(k+1) → k = AUC/(1-AUC).
        if target_auc >= 0.5:
            k = max(1e-3, target_auc / (1.0 - target_auc))
            tpr = 1.0 - (1.0 - fpr) ** k
        else:
            # Below-chance curves: mirror around the diagonal.
            k = max(1e-3, (1.0 - target_auc) / target_auc)
            tpr = fpr ** k
        tpr = np.clip(tpr + rng.normal(0.0, jitter, fpr.size), 0.0, 1.0)
        # Anchor endpoints.
        tpr[0], tpr[-1] = 0.0, 1.0
        return fpr.tolist(), tpr.tolist()

    # Manuscript Fig 3G values: female AUC=0.375 (n=8 mice),
    # male AUC=0.583 (n=7 mice).
    fpr_f, tpr_f = _make_roc(0.375)
    fpr_m, tpr_m = _make_roc(0.583)
    entries = [
        LOOCVAUCEntry(
            stratum="female", fpr=fpr_f, tpr=tpr_f,
            auc=0.375, auc_ci_lo=0.18, auc_ci_hi=0.58,
            n_subjects=8,
        ),
        LOOCVAUCEntry(
            stratum="male", fpr=fpr_m, tpr=tpr_m,
            auc=0.583, auc_ci_lo=0.36, auc_ci_hi=0.78,
            n_subjects=7,
        ),
    ]
    return SexStratifiedROCInput(entries=entries)


_META = RecipeMetadata(
    name="sex_stratified_roc_loocv",
    modality="mixed_effects_models",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "How well does a classifier separate phenotypes per sex stratum "
        "under leave-one-out cross-validation, and how does the AUC "
        "compare across strata?"
    ),
    required_fields=("entries",),
    optional_fields=("title",),
    file_format_hints=("csv", "yaml"),
    alternatives_in_modality=("sex_x_genotype_interaction_forest",),
    statistical_contract=StatisticalContract(
        min_n_per_group=10,
        distribution_assumption="approximately_gaussian",
        multiple_comparisons="any_correction_required",
        independence="iid",
        effect_size_in_units="standardized_d",
        rendered_claim_template="Cohen's d = {d:.2f} ({outcome_class})",
        refuses_when=("underpowered",),
    ),
)


@register_recipe(
    metadata=_META,
    contract=SexStratifiedROCInput,
    demo_contract=_demo,
)
def render(contract: SexStratifiedROCInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.4, 4.0))
    AESTHETIC.apply_to_ax(ax)

    # Diagonal chance line — satisfies one of the family fit-lines.
    ax.plot([0.0, 1.0], [0.0, 1.0], color="#888888",
            ls="--", lw=0.7, zorder=1, label="chance (AUC = 0.5)")

    # Per-stratum colours.
    palette = {"female": "#E91E63", "male": "#1976D2"}
    fallback = ["#37474F", "#FFB300", "#26A69A"]

    for i, e in enumerate(contract.entries):
        colour = palette.get(e.stratum.lower(), fallback[i % len(fallback)])
        fpr = np.asarray(e.fpr, float)
        tpr = np.asarray(e.tpr, float)

        # Per-fold scatter (the >=1 scatter for the family rule).
        ax.scatter(fpr, tpr, s=14, color=colour, alpha=0.55,
                   edgecolor="white", linewidth=0.4, zorder=3,
                   marker="o")

        # Smoothed ROC line (the fit line) — sort by FPR + cumulative max
        # of TPR to keep monotonic non-decreasing.
        order = np.argsort(fpr)
        fpr_s = fpr[order]
        tpr_s = np.maximum.accumulate(tpr[order])

        ci_str = ""
        if e.auc_ci_lo is not None and e.auc_ci_hi is not None:
            ci_str = f"  [{smart_fmt(e.auc_ci_lo)}–{smart_fmt(e.auc_ci_hi)}]"
        ax.plot(fpr_s, tpr_s, color=colour, lw=1.4, alpha=0.92, zorder=4,
                label=f"{e.stratum}  ·  AUC={smart_fmt(e.auc)}{ci_str}  "
                      f"·  n={e.n_subjects}")

    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.05)
    ax.set_xlabel("1 - specificity (FPR)")
    ax.set_ylabel("sensitivity (TPR)")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    ax.legend(fontsize=6.4, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.18),
              ncols=1, handlelength=1.4)

    ax.set_title(contract.title, fontsize=8.2, pad=4)
    return ax
