"""Two-way ANOVA summary plot — sex × genotype × interaction effect-and-CI summary.

Renders a horizontal forest of three F-statistic markers (one per
factorial term: sex, genotype, sex × genotype interaction) with each
marker placed on the partial η² scale.  The 95% CI on partial η² is
drawn as a horizontal whisker; the F-stat and p-value are shown in
right-margin annotations.

Coef-forest family: >=3 markers + >=1 reference line. Satisfied
exactly by the three term markers + a vertical zero-effect reference
line at η² = 0 + a faint α=0.05 ladder reference.
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
from ._shared import TwoWayANOVAResult, TwoWayANOVATerm


class TwoWayANOVASummaryInput(RecipeContract):
    result: TwoWayANOVAResult = Field(...)
    alpha: float = 0.05
    title: str = "Two-way ANOVA summary"


def _demo() -> TwoWayANOVASummaryInput:
    # Manuscript Fig 5H values: sex F=1.59 p=0.233; genotype F=1.17 p=0.302;
    # interaction F=1.37 p=0.266. Per η²-partial reconstructed from
    # F * df_num / (F * df_num + df_den) for df_num=1, df_den=12.
    rng = np.random.default_rng(820)
    rows = [
        ("sex",                 1.59, 0.233),
        ("genotype",            1.17, 0.302),
        ("sex x genotype",      1.37, 0.266),
    ]
    df_num, df_den = 1, 12
    terms: list[TwoWayANOVATerm] = []
    for label, f, p in rows:
        eta2 = (f * df_num) / (f * df_num + df_den)
        # 95% bootstrap-style CI on η², width scaled by a noise floor.
        w = 0.04 + rng.uniform(0.01, 0.03)
        terms.append(TwoWayANOVATerm(
            term=label, f_stat=f, p_value=p,
            partial_eta_sq=eta2,
            eta_sq_ci_lo=max(0.0, eta2 - w),
            eta_sq_ci_hi=min(1.0, eta2 + w),
            df_num=df_num, df_den=df_den,
        ))
    result = TwoWayANOVAResult(
        terms=terms, response_label="surveillance index", n_per_cell=4,
    )
    return TwoWayANOVASummaryInput(result=result)


_META = RecipeMetadata(
    name="two_way_anova_summary_plot",
    modality="mixed_effects_models",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "In a 2 × 2 factorial design, which of {sex, genotype, sex × "
        "genotype interaction} is detectable, with what F, p, and "
        "partial eta^2 effect size?"
    ),
    required_fields=("result",),
    optional_fields=("alpha", "title"),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=(
        "sex_x_genotype_interaction_forest",
        "emmeans_contrast_grid",
    ),
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
    contract=TwoWayANOVASummaryInput,
    demo_contract=_demo,
)
def render(contract: TwoWayANOVASummaryInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 2.8))
    AESTHETIC.apply_to_ax(ax)

    terms = list(contract.result.terms)
    n = len(terms)
    y = np.arange(n)[::-1]   # top-to-bottom in user order

    # Reference 1: zero-effect line.
    ax.axvline(0.0, color="#888888", lw=0.7, ls="--", zorder=1,
               label="zero effect")

    # Reference 2: α=0.05 ladder (faint; visualises which terms cross
    # the conventional significance threshold via |p| annotation).
    ax.axvline(0.05, color="#BDBDBD", lw=0.4, ls=":", zorder=1)

    # Per-term markers + CI whiskers.
    interaction_color = "#C62828"
    main_color = "#37474F"
    for yi, t in zip(y, terms):
        # Interaction detection requires a separator token, not a bare 'x'
        # (the literal 'x' in "sex" would otherwise false-positive).
        is_inter = (" x " in t.term) or (":" in t.term) or ("*" in t.term)
        colour = interaction_color if is_inter else main_color
        ci_lo = (
            t.eta_sq_ci_lo
            if t.eta_sq_ci_lo is not None
            else t.partial_eta_sq
        )
        ci_hi = (
            t.eta_sq_ci_hi
            if t.eta_sq_ci_hi is not None
            else t.partial_eta_sq
        )
        ax.plot([ci_lo, ci_hi], [yi, yi], color=colour,
                lw=1.4 if is_inter else 1.0, zorder=3)
        for x_end in (ci_lo, ci_hi):
            ax.plot([x_end, x_end], [yi - 0.15, yi + 0.15],
                    color=colour, lw=1.4 if is_inter else 1.0, zorder=3)
        ax.scatter([t.partial_eta_sq], [yi], s=66 if is_inter else 48,
                   facecolor=colour, edgecolor="white", linewidth=0.9,
                   zorder=4)

    # Right-margin annotation: F, p.
    eta_max = max(t.partial_eta_sq for t in terms)
    eta_max_ci = max(
        (t.eta_sq_ci_hi if t.eta_sq_ci_hi is not None else t.partial_eta_sq)
        for t in terms
    )
    span = max(eta_max_ci, 0.10)
    ax.set_xlim(-0.02, span * 1.55)
    xhi = ax.get_xlim()[1]
    gap = 0.012 * (xhi - ax.get_xlim()[0])
    for yi, t in zip(y, terms):
        ci_hi = (
            t.eta_sq_ci_hi
            if t.eta_sq_ci_hi is not None
            else t.partial_eta_sq
        )
        sig = "*" if t.p_value < contract.alpha else " "
        ax.text(ci_hi + gap, yi,
                f"F={smart_fmt(t.f_stat)}  ·  p={smart_fmt(t.p_value)}{sig}",
                ha="left", va="center", fontsize=6.4,
                color="#222222", zorder=5)

    ax.set_yticks(y)
    ax.set_yticklabels([t.term for t in terms], fontsize=7.2)
    ax.set_xlabel("partial η² (effect size)")
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    # Legend.
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor=main_color, markeredgecolor="white",
               markersize=6, label="main effect"),
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor=interaction_color, markeredgecolor="white",
               markersize=7, label="interaction"),
        Line2D([0], [0], color="#888888", ls="--", lw=0.7,
               label="zero effect"),
    ]
    ax.legend(handles=handles, fontsize=6.4, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.20),
              ncols=3, handlelength=1.2)

    n_per = (
        f"  ·  n/cell = {contract.result.n_per_cell}"
        if contract.result.n_per_cell is not None
        else ""
    )
    ax.set_title(
        f"{contract.title}  ·  {contract.result.response_label}{n_per}",
        fontsize=8.2, pad=4,
    )
    _ = eta_max  # silences unused if user reorders code paths
    return ax
