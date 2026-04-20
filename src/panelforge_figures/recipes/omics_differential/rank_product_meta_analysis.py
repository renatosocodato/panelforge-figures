"""Cross-study rank-product meta-analysis — genes consistent across N studies.

For each gene, a combined rank-product (or rank-sum) across N studies
is plotted as a horizontal bar sorted best-first, with permutation-FDR
significance markers. A companion strip of per-study ranks (coloured)
lets the reader see which studies contribute most.
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


class RankProductInput(RecipeContract):
    gene_names: list[str] = Field(..., min_length=3)
    per_study_ranks: list[list[float]] = Field(
        ..., description="N_genes × N_studies rank matrix (1 = best)"
    )
    rank_product: list[float] = Field(
        ..., description="combined rank product per gene"
    )
    p_value: list[float] | None = None
    study_names: list[str] | None = None
    top_n: int = 15
    title: str = "Rank-product meta-analysis"


def _demo() -> RankProductInput:
    rng = np.random.default_rng(823)
    n_studies = 4
    n_genes_total = 50
    genes = [f"g{i:03d}" for i in range(n_genes_total)]
    # Ranks: some genes consistently small (good), others noisy.
    ranks = rng.integers(1, 800, (n_genes_total, n_studies)).astype(float)
    for i in range(10):
        ranks[i] = rng.integers(1, 60, n_studies)
    rp = np.exp(np.mean(np.log(ranks), axis=1))
    p = np.minimum(1.0, rp / rp.max())
    order = np.argsort(rp)
    return RankProductInput(
        gene_names=[genes[i] for i in order],
        per_study_ranks=ranks[order].tolist(),
        rank_product=rp[order].tolist(),
        p_value=p[order].tolist(),
        study_names=[f"study_{k+1}" for k in range(n_studies)],
        top_n=15,
    )


_META = RecipeMetadata(
    name="rank_product_meta_analysis",
    modality="omics_differential",
    family=RecipeFamily.ladder,
    answers_question=(
        "Across multiple studies, which genes are consistently "
        "high-ranking by the rank-product meta-analysis statistic?"
    ),
    required_fields=("gene_names", "per_study_ranks", "rank_product"),
    optional_fields=("p_value", "study_names", "top_n", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("differential_rank_ladder",),
)


@register_recipe(
    metadata=_META,
    contract=RankProductInput,
    demo_contract=_demo,
)
def render(contract: RankProductInput, ax=None, **_):
    import matplotlib as mpl

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.0, 4.0))
    AESTHETIC.apply_to_ax(ax)

    names = contract.gene_names
    rp = np.asarray(contract.rank_product, float)
    ranks = np.asarray(contract.per_study_ranks, float)
    p = (np.asarray(contract.p_value, float)
         if contract.p_value is not None else None)

    # Take top-N.
    top_n = min(contract.top_n, len(names))
    idx = np.argsort(rp)[:top_n]
    names_top = [names[i] for i in idx]
    rp_top = rp[idx]
    ranks_top = ranks[idx]
    p_top = p[idx] if p is not None else None

    y = np.arange(top_n)[::-1]

    # Main bar: rank-product (lower = better; flip so longer = better).
    # Display as 1/rp on a log axis for readability.
    xbar = 1.0 / np.maximum(rp_top, 1e-6)
    ax.barh(y, xbar, height=0.55, color="#455A64",
            edgecolor="white", linewidth=0.5, alpha=0.85, zorder=3)

    # Significance star / dot for p < 0.05.
    if p_top is not None:
        for yi, pi in zip(y, p_top):
            if pi < 0.05:
                ax.scatter([xbar[list(y).index(yi)]], [yi], marker="*",
                           s=90, color="#D32F2F", edgecolor="white",
                           linewidth=0.6, zorder=5,
                           clip_on=False)

    # Right-of-bar numeric labels.
    gap = xbar.max() * 0.02
    for yi, xi, rpi in zip(y, xbar, rp_top):
        ax.text(xi + gap, yi,
                f"RP={smart_fmt(float(rpi))}",
                va="center", ha="left", fontsize=6.4,
                color="#222222", zorder=5)

    # Per-study rank strip placed to the RIGHT of the bars so it never
    # collides with gene labels on the y-axis.
    n_studies = ranks_top.shape[1]
    study_names = (contract.study_names
                   or [f"s{k}" for k in range(n_studies)])
    cmap = mpl.colormaps["viridis"]
    max_rank = max(ranks_top.max(), 1.0)
    strip_x0 = 1.12      # axes-fraction x (right of bars + RP text)
    strip_dx = 0.045
    for yi, row in zip(y, ranks_top):
        for si, rk in enumerate(row):
            color = cmap(0.1 + 0.85 * (1 - rk / max_rank))
            ax.scatter([strip_x0 + si * strip_dx], [yi],
                       s=22, color=color, edgecolor="white",
                       linewidth=0.3, zorder=6,
                       transform=ax.get_yaxis_transform(),
                       clip_on=False)
    # Study labels above the strip.
    for si, nm in enumerate(study_names):
        ax.text(strip_x0 + si * strip_dx, top_n - 0.4, nm,
                transform=ax.get_yaxis_transform(),
                ha="center", va="bottom", fontsize=5.6,
                color="#333333", rotation=35,
                clip_on=False)

    ax.set_yticks(y)
    ax.set_yticklabels(names_top, fontsize=7.0)
    ax.set_xlabel("1 / rank-product  (longer bar = more consistent)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.set_xlim(0, xbar.max() * 1.30)
    # Reserve additional right margin so the per-study strip fits.
    ax.figure.subplots_adjust(right=0.70)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
