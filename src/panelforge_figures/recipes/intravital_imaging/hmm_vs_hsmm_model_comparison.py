"""HMM vs HSMM model comparison — forest plot of delta-criterion
(HSMM minus HMM) per stratum, with bootstrap CI from CV folds.

Adjudicator recipe: when both models have been fit, this panel
gives the per-stratum verdict. Negative delta-BIC = HSMM wins
(non-geometric dwells); positive = HMM wins (geometric dwells).
The CI bars show whether the delta is significant.

Coef-forest family: >=3 markers + >=1 reference line. Satisfied by
>=3 stratum rows + the zero-delta reference at x=0.
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
from ._shared import ModelFitSummary


class HMMvsHSMMComparisonInput(RecipeContract):
    fits: list[ModelFitSummary] = Field(..., min_length=6)
    reference_model: str = Field(
        "HMM", description="'HMM' or 'HSMM'; delta = other - reference",
    )
    criterion: str = Field(
        "BIC", description="'AIC' | 'BIC' | 'CV'",
    )
    title: str = "HMM vs HSMM model comparison"


def _demo() -> HMMvsHSMMComparisonInput:
    rng = np.random.default_rng(1741)
    strata = ["control", "treated", "DISC1", "rescue"]
    fits: list[ModelFitSummary] = []
    for stratum in strata:
        # Synthetic: HSMM wins by ~12-25 BIC units in 3 of 4 strata.
        if stratum == "control":
            hmm_bic = 8200.0 + rng.normal(0, 2)
            hsmm_bic = 8203.0 + rng.normal(0, 3)  # tied
        elif stratum == "rescue":
            hmm_bic = 7950.0 + rng.normal(0, 2)
            hsmm_bic = 7945.0 + rng.normal(0, 3)  # weak HSMM win
        else:
            hmm_bic = 8400.0 + rng.normal(0, 2)
            hsmm_bic = 8378.0 + rng.normal(0, 3)  # clear HSMM win
        fits.append(ModelFitSummary(
            stratum=stratum, model="HMM", n_states=3,
            log_likelihood=-(hmm_bic - 30) / 2, aic=hmm_bic - 30,
            bic=hmm_bic,
            cv_log_likelihood_mean=-hmm_bic / 2,
            cv_log_likelihood_sd=2.5,
        ))
        fits.append(ModelFitSummary(
            stratum=stratum, model="HSMM", n_states=3,
            log_likelihood=-(hsmm_bic - 60) / 2, aic=hsmm_bic - 60,
            bic=hsmm_bic,
            cv_log_likelihood_mean=-hsmm_bic / 2,
            cv_log_likelihood_sd=2.8,
        ))
    return HMMvsHSMMComparisonInput(fits=fits)


_META = RecipeMetadata(
    name="hmm_vs_hsmm_model_comparison",
    modality="intravital_imaging",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "Across strata, does HSMM (semi-Markov, age-dependent dwell) "
        "beat HMM (Markov, geometric dwell) by AIC / BIC / CV log-lik?"
    ),
    required_fields=("fits",),
    optional_fields=("reference_model", "criterion", "title"),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("dwell_time_distribution_per_state",),
)


@register_recipe(
    metadata=_META,
    contract=HMMvsHSMMComparisonInput,
    demo_contract=_demo,
)
def render(contract: HMMvsHSMMComparisonInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.8, 3.6))
    AESTHETIC.apply_to_ax(ax)

    # Group fits by stratum.
    by_stratum: dict[str, dict[str, ModelFitSummary]] = {}
    for f in contract.fits:
        by_stratum.setdefault(f.stratum, {})[f.model] = f

    other_model = "HSMM" if contract.reference_model == "HMM" else "HMM"
    strata = list(by_stratum.keys())
    deltas: list[float] = []
    delta_los: list[float] = []
    delta_his: list[float] = []
    valid_strata: list[str] = []

    for stratum in strata:
        pair = by_stratum[stratum]
        if contract.reference_model not in pair or other_model not in pair:
            continue
        ref = pair[contract.reference_model]
        other = pair[other_model]
        if contract.criterion == "AIC":
            delta = float(other.aic - ref.aic)
            # CI from sqrt(n_params) heuristic; if cv_log_likelihood_sd
            # is available, use 2 * sd as a CI half-width proxy.
            half = 2.0 * ((ref.cv_log_likelihood_sd or 0.0)
                          + (other.cv_log_likelihood_sd or 0.0))
        elif contract.criterion == "BIC":
            delta = float(other.bic - ref.bic)
            half = 2.0 * ((ref.cv_log_likelihood_sd or 0.0)
                          + (other.cv_log_likelihood_sd or 0.0))
        else:  # CV
            delta = -2.0 * float(
                (other.cv_log_likelihood_mean or 0.0)
                - (ref.cv_log_likelihood_mean or 0.0)
            )
            half = 2.0 * ((ref.cv_log_likelihood_sd or 0.0)
                          + (other.cv_log_likelihood_sd or 0.0))
        deltas.append(delta)
        delta_los.append(delta - half)
        delta_his.append(delta + half)
        valid_strata.append(stratum)

    if not deltas:
        ax.set_title(contract.title, fontsize=8.4, pad=4)
        return ax

    y = np.arange(len(valid_strata))

    # Reference at zero (no model preference).
    ax.axvline(0, color="#888888", lw=0.7, ls="--", zorder=2,
               label=f"{contract.reference_model} = {other_model}")
    ax.axvline(-10, color="#1565C0", lw=0.5, ls=":", alpha=0.6, zorder=1)
    ax.axvline(10, color="#C62828", lw=0.5, ls=":", alpha=0.6, zorder=1)

    # CI segments + markers.
    for yi, d, lo, hi in zip(y, deltas, delta_los, delta_his):
        # Negative delta -> blue (HSMM wins if reference=HMM); positive -> red.
        colour = "#1565C0" if d < 0 else "#C62828"
        ax.plot([lo, hi], [yi, yi],
                color=colour, lw=1.1, alpha=0.85, zorder=3)
    ax.scatter(deltas, y, s=44,
               c=["#1565C0" if d < 0 else "#C62828" for d in deltas],
               edgecolor="white", linewidth=0.5, zorder=5)

    # Per-row verdict text.
    for yi, d in zip(y, deltas):
        verdict = (f"HSMM by {smart_fmt(abs(d))}" if d < 0
                   else f"HMM by {smart_fmt(d)}")
        ax.text(max(delta_his) * 1.05, yi,
                verdict, ha="left", va="center", fontsize=6.4,
                color="#333333")

    ax.set_yticks(y)
    ax.set_yticklabels(valid_strata, fontsize=7.0)
    ax.invert_yaxis()
    ax.set_xlabel(
        f"delta-{contract.criterion}  "
        f"({other_model} - {contract.reference_model})  "
        f"-->  negative = {other_model} wins"
    )
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    # Legend above the axes (lower-right collided with the per-row
    # verdict labels which extend to the right edge).
    ax.legend(fontsize=6.6, frameon=False, loc="lower right",
              bbox_to_anchor=(1.0, 1.02), handlelength=1.4)

    n_other_wins = sum(1 for d in deltas if d < 0)
    n_total = len(deltas)
    ax.set_title(
        f"{contract.title}  ·  criterion = {contract.criterion}  ·  "
        f"{other_model} wins {n_other_wins}/{n_total} strata",
        fontsize=8.2, pad=4,
    )
    return ax
