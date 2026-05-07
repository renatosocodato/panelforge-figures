"""Cross-contrast correlation matrix — N × N grid of pairwise
correlations between contrasts (e.g. female-CTL-vs-CKO,
male-CTL-vs-CKO, sex-baseline) on a diverging cmap, with diagonal
masked.

Matrix family: >=1 imshow OR >=4 cell patches.
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


class CrossContrastCorrelationInput(RecipeContract):
    contrast_labels: list[str] = Field(..., min_length=3)
    correlation: list[list[float]] = Field(...)
    title: str = "Cross-contrast correlation matrix"


def _demo() -> CrossContrastCorrelationInput:
    rng = np.random.default_rng(803)
    contrasts = [
        "F: CTL vs CKO",
        "M: CTL vs CKO",
        "F vs M baseline",
        "F vs M after",
        "CTL vs CKO pooled",
    ]
    n = len(contrasts)
    R = np.eye(n)
    # Off-diagonals: mostly low (~0.20) reflecting non-overlap.
    for i in range(n):
        for j in range(i + 1, n):
            r = float(rng.normal(0.20, 0.08))
            r = float(np.clip(r, -0.9, 0.9))
            R[i, j] = r
            R[j, i] = r
    return CrossContrastCorrelationInput(
        contrast_labels=contrasts,
        correlation=R.tolist(),
    )


_META = RecipeMetadata(
    name="cross_contrast_correlation_matrix",
    modality="meta_and_diagnostic",
    family=RecipeFamily.matrix,
    answers_question=(
        "Across pairwise contrasts, how correlated are the "
        "per-feature effect-size estimates, and where in the grid "
        "do contrasts converge or remain independent?"
    ),
    required_fields=("contrast_labels", "correlation"),
    optional_fields=("title",),
    file_format_hints=("csv", "yaml"),
    alternatives_in_modality=("reproducibility_correlogram",),
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
    contract=CrossContrastCorrelationInput,
    demo_contract=_demo,
)
def render(contract: CrossContrastCorrelationInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.8, 4.4))
    AESTHETIC.apply_to_ax(ax)

    R = np.asarray(contract.correlation, float)
    n = R.shape[0]
    labels = contract.contrast_labels

    # Mask diagonal to highlight off-diagonal structure.
    R_show = np.ma.masked_array(R, mask=np.eye(n, dtype=bool))
    im = ax.imshow(R_show, cmap="RdBu_r",
                   vmin=-1.0, vmax=1.0,
                   aspect="equal", interpolation="nearest", zorder=2)

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.04, pad=0.03)
    cbar.set_label("correlation", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.0)

    # Annotate cells.
    for i in range(n):
        for j in range(n):
            if i == j:
                ax.text(j, i, "—", ha="center", va="center",
                        fontsize=7.0, color="#999999", zorder=4)
            else:
                v = R[i, j]
                txt_color = "white" if abs(v) > 0.55 else "#222222"
                ax.text(j, i, f"{smart_fmt(v)}",
                        ha="center", va="center", fontsize=6.4,
                        color=txt_color, zorder=4)

    ax.set_xticks(range(n))
    ax.set_xticklabels(labels, fontsize=6.6, rotation=20, ha="right")
    ax.set_yticks(range(n))
    ax.set_yticklabels(labels, fontsize=6.6)
    ax.tick_params(axis="x", which="major", pad=2)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    # Mean off-diagonal correlation as a headline.
    iu = np.triu_indices(n, k=1)
    mean_off = float(np.mean(R[iu]))
    ax.set_title(
        f"{contract.title}  ·  n_contrasts = {n}  ·  "
        f"mean off-diag r = {smart_fmt(mean_off)}",
        fontsize=8.2, pad=4,
    )
    return ax
