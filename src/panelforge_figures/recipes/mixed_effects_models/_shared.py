"""Shared sub-contracts for the `mixed_effects_models` modality.

Pioneered by the `factorial_design_companion` Wave 3 pack. Existing
recipes in this modality used inline contracts because no shared
sub-contracts were needed; Wave 3 introduces four reusable atoms
that recur across the F3G / F4H / F4I / F5H factorial-statistics
panel cluster.

Future packs that extend factorial-design model figures (multi-way
ANOVA, mediation, paired pre/post slopes, sex/genotype-stratified
ROC) reuse these sub-contracts directly.
"""

from __future__ import annotations

from pydantic import Field

from ...core import RecipeContract

# --- two-way ANOVA atoms ----------------------------------------------------


class TwoWayANOVATerm(RecipeContract):
    """One ANOVA term's F-statistic + p-value + partial η² + 95% CI.

    Used by W3.1 (`two_way_anova_summary_plot`). The three canonical
    terms in a 2 × 2 factorial are sex, genotype, and the sex × genotype
    interaction; the recipe renders them as a horizontal forest of
    F-stat markers anchored on the partial η² scale.
    """
    term: str                                  # "sex" | "genotype" | "sex x genotype"
    f_stat: float
    p_value: float
    partial_eta_sq: float                      # effect size on [0, 1]
    eta_sq_ci_lo: float | None = None
    eta_sq_ci_hi: float | None = None
    df_num: int | None = None
    df_den: int | None = None


class TwoWayANOVAResult(RecipeContract):
    """Bundle of three ANOVA terms (sex, genotype, interaction) plus
    optional response label.

    Used by W3.1.
    """
    terms: list[TwoWayANOVATerm] = Field(..., min_length=3)
    response_label: str = "outcome"
    n_per_cell: int | None = None              # n per (sex, genotype) cell


# --- LOOCV ROC atoms --------------------------------------------------------


class LOOCVAUCEntry(RecipeContract):
    """One stratum's LOOCV ROC curve (FPR, TPR) + AUC + n_subjects.

    Used by W3.2 (`sex_stratified_roc_loocv`). Each entry carries the
    per-stratum decoded curve (one (1 - specificity, sensitivity) pair
    per left-out subject), AUC (estimated by the trapezoidal rule),
    and a 95% bootstrap CI on the AUC.
    """
    stratum: str                               # "female" | "male" | etc.
    fpr: list[float]                           # 1 - specificity values
    tpr: list[float]                           # sensitivity values
    auc: float
    auc_ci_lo: float | None = None
    auc_ci_hi: float | None = None
    n_subjects: int


# --- mediation atoms --------------------------------------------------------


class MediationPath(RecipeContract):
    """One stratum's direct + indirect effect estimates.

    Used by W3.3 (`mediation_decomposition_slope_chart`). Direct =
    treatment → outcome holding mediator fixed; indirect = treatment
    → mediator → outcome (the mediated portion). Total effect is the
    sum (when on the additive scale).
    """
    stratum: str                               # "female · CTL" | "male · CKO" | etc.
    direct_effect: float
    direct_ci_lo: float
    direct_ci_hi: float
    indirect_effect: float
    indirect_ci_lo: float
    indirect_ci_hi: float
    proportion_mediated: float | None = None   # in [0, 1]


# --- paired pre/post slope atoms --------------------------------------------


class PrePostSlopeRow(RecipeContract):
    """One module × condition pre/post score pair.

    Used by W3.4 (`pre_post_slope_chart_by_module`). Each row is
    a single module (pathway / GEF-GAP-effector module) measured
    pre and post intervention in one stratum (sex × genotype cell).
    The recipe renders connecting slope lines per module with
    per-condition colour.
    """
    module: str                                # e.g. "GEF · Vav1"
    condition: str                             # "female · CTL" | "male · CKO" | ...
    pre_score: float
    post_score: float
    is_significant: bool = False               # raises slope line weight
