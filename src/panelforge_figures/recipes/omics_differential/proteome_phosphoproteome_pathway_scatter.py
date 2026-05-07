"""Proteome × phosphoproteome pathway scatter — per-pathway scatter
of proteome sex-effect score (x) vs phospho sex-effect score (y),
with Spearman ρ + OLS fit and zero-correlation reference axes.
The manuscript's headline finding is *near-zero concordance* — the
scatter is meant to look unstructured by design.

Scatter-collapse family: >=1 scatter + >=1 fit line.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field
from scipy import stats

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    StatisticalContract,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC
from ._shared import ProteomePhosphoConcordanceRow


class ProteomePhosphoScatterInput(RecipeContract):
    rows: list[ProteomePhosphoConcordanceRow] = Field(..., min_length=10)
    title: str = "Proteome × phosphoproteome pathway scatter"


def _demo() -> ProteomePhosphoScatterInput:
    rng = np.random.default_rng(811)
    rows: list[ProteomePhosphoConcordanceRow] = []
    n = 430
    # Near-zero correlation by design.
    proteome = rng.normal(0, 0.4, n)
    phospho = rng.normal(0, 0.5, n)
    # GGE-flagged pathways form ~10% of the set.
    is_gge = rng.random(n) < 0.10
    for k in range(n):
        rows.append(ProteomePhosphoConcordanceRow(
            pathway=f"R-PATH-{k:04d}",
            proteome_score=float(proteome[k]),
            phospho_score=float(phospho[k]),
            n_proteins=int(rng.integers(3, 80)),
            branch="GGE" if is_gge[k] else "non_GGE",
        ))
    return ProteomePhosphoScatterInput(rows=rows)


_META = RecipeMetadata(
    name="proteome_phosphoproteome_pathway_scatter",
    modality="omics_differential",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "At pathway level, how concordant are proteome and "
        "phosphoproteome sex-effect scores, and is the relationship "
        "consistent with independent biological dimensions?"
    ),
    required_fields=("rows",),
    optional_fields=("title",),
    file_format_hints=("csv", "yaml"),
    alternatives_in_modality=("effect_size_replicate_concordance",),
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
    contract=ProteomePhosphoScatterInput,
    demo_contract=_demo,
)
def render(contract: ProteomePhosphoScatterInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 4.2))
    AESTHETIC.apply_to_ax(ax)

    proteome = np.array([r.proteome_score for r in contract.rows])
    phospho = np.array([r.phospho_score for r in contract.rows])
    is_gge = np.array([r.branch == "GGE" for r in contract.rows])

    # Reference axes (zero lines).
    ax.axhline(0, color="#888888", lw=0.7, ls="--", zorder=2,
               label="zero phospho")
    ax.axvline(0, color="#888888", lw=0.7, ls="--", zorder=2)

    # Per-pathway scatter — non-GGE behind, GGE on top.
    ax.scatter(proteome[~is_gge], phospho[~is_gge],
               s=14, color="#9E9E9E", alpha=0.45,
               edgecolor="none", zorder=3, label="non-GGE pathways")
    ax.scatter(proteome[is_gge], phospho[is_gge],
               s=22, color="#26A69A", alpha=0.85,
               edgecolor="white", linewidth=0.4, zorder=5,
               label="GGE pathways")

    # OLS fit (the >=1 fit line for the family rule).  Pearson
    # statistics are not displayed (Spearman ρ is the manuscript's
    # headline statistic), so just capture slope + intercept.
    if proteome.size > 1:
        result = stats.linregress(proteome, phospho)
        slope = float(result.slope)
        intercept = float(result.intercept)
        x_grid = np.linspace(float(proteome.min()),
                             float(proteome.max()), 50)
        ax.plot(x_grid, slope * x_grid + intercept,
                color="#37474F", lw=1.2, alpha=0.85,
                zorder=6, label="OLS fit")

    # Spearman rho callout.
    rho_spearman, p_spearman = stats.spearmanr(proteome, phospho)

    ax.set_xlabel("proteome sex-effect score")
    ax.set_ylabel("phospho sex-effect score")
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(fontsize=6.4, frameon=False, loc="upper right",
              handlelength=1.2)

    ax.set_title(
        f"{contract.title}  ·  n = {len(contract.rows)} pathways  ·  "
        f"Spearman ρ = {smart_fmt(float(rho_spearman))}  "
        f"(p = {smart_fmt(float(p_spearman))})",
        fontsize=8.2, pad=4,
    )
    return ax
