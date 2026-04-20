"""Replicate-1 vs replicate-2 effect-size concordance scatter.

For the same contrast measured in two biological replicates (or a
discovery / validation pair), each gene becomes a dot in
(rep1_log2FC, rep2_log2FC) space. An identity line, a fitted OLS
regression, Pearson r and a 95 % agreement band (Bland-Altman-style
SD×1.96) quantify concordance.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    density_alpha,
    empty_data_guard,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class ReplicateConcordanceInput(RecipeContract):
    gene_names: list[str] = Field(...)
    rep1_log2fc: list[float] = Field(...)
    rep2_log2fc: list[float] = Field(...)
    rep1_label: str = "replicate 1"
    rep2_label: str = "replicate 2"
    title: str = "Replicate concordance"


def _demo() -> ReplicateConcordanceInput:
    rng = np.random.default_rng(509)
    n = 1800
    names = [f"g{i:05d}" for i in range(n)]
    r1 = rng.normal(0, 0.9, n)
    # Rep2 highly correlated plus measurement noise.
    r2 = 0.92 * r1 + rng.normal(0, 0.35, n)
    # Inject a few outliers.
    outliers = rng.choice(n, size=14, replace=False)
    r2[outliers] = -r1[outliers] + rng.normal(0, 0.2, outliers.size)
    return ReplicateConcordanceInput(
        gene_names=names,
        rep1_log2fc=r1.tolist(),
        rep2_log2fc=r2.tolist(),
        rep1_label="rep A",
        rep2_label="rep B",
    )


_META = RecipeMetadata(
    name="effect_size_replicate_concordance",
    modality="omics_differential",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Across biological replicates of the same contrast, how well "
        "do effect-size estimates agree per gene?"
    ),
    required_fields=("gene_names", "rep1_log2fc", "rep2_log2fc"),
    optional_fields=("rep1_label", "rep2_label", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("effect_size_vs_significance",),
)


@register_recipe(
    metadata=_META,
    contract=ReplicateConcordanceInput,
    demo_contract=_demo,
)
def render(contract: ReplicateConcordanceInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.6, 4.2))
    AESTHETIC.apply_to_ax(ax)
    if empty_data_guard(ax, len(contract.rep1_log2fc), message="no genes"):
        return ax

    r1 = np.asarray(contract.rep1_log2fc, float)
    r2 = np.asarray(contract.rep2_log2fc, float)
    mask = np.isfinite(r1) & np.isfinite(r2)
    r1 = r1[mask]
    r2 = r2[mask]

    # Density alpha for big N.
    alpha = density_alpha(r1, r2) if r1.size else np.array([])
    ax.scatter(r1, r2, s=8, c="#455A64", alpha=alpha,
               edgecolor="none", zorder=2, label="genes")

    # Identity line y = x.
    lo = float(min(r1.min(), r2.min()))
    hi = float(max(r1.max(), r2.max()))
    span = hi - lo
    ax.plot([lo - 0.05 * span, hi + 0.05 * span],
            [lo - 0.05 * span, hi + 0.05 * span],
            color="#111111", lw=0.8, ls="--", zorder=3,
            label="y = x")

    # OLS fit through (r1, r2).
    slope, intercept = np.polyfit(r1, r2, 1)
    xs = np.linspace(lo, hi, 80)
    ax.plot(xs, slope * xs + intercept, color="#D32F2F", lw=1.2, zorder=4,
            label=f"OLS: slope={smart_fmt(float(slope))}")

    # 95 % agreement band (±1.96 × SD of residuals from identity).
    diff = r2 - r1
    sd = float(np.std(diff))
    band = 1.96 * sd
    ax.fill_between(
        [lo - 0.05 * span, hi + 0.05 * span],
        [(lo - 0.05 * span) - band, (hi + 0.05 * span) - band],
        [(lo - 0.05 * span) + band, (hi + 0.05 * span) + band],
        color="#888888", alpha=0.10, zorder=1,
        label=f"95% LoA (±{smart_fmt(band)})",
    )

    r = float(np.corrcoef(r1, r2)[0, 1])

    ax.set_xlabel(contract.rep1_label + r"  $\log_2$FC")
    ax.set_ylabel(contract.rep2_label + r"  $\log_2$FC")
    ax.set_xlim(lo - 0.05 * span, hi + 0.05 * span)
    ax.set_ylim(lo - 0.05 * span, hi + 0.05 * span)
    ax.set_aspect("equal")
    ax.set_title(
        f"{contract.title}  ·  N={int(r1.size)}, r={smart_fmt(r)}",
        fontsize=9.0, pad=4,
    )
    ax.legend(fontsize=6.6, frameon=False, loc="center left",
              bbox_to_anchor=(1.02, 0.5), handlelength=1.6)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    ax.text(
        0.98, 0.03,
        f"bias = {smart_fmt(float(diff.mean()))}\n"
        f"SD(Δ) = {smart_fmt(sd)}",
        transform=ax.transAxes, ha="right", va="bottom",
        fontsize=6.4, color="#333333",
        bbox=dict(boxstyle="round,pad=0.22", fc="white",
                  ec="#BBBBBB", lw=0.5, alpha=0.92),
        zorder=6,
    )
    return ax
