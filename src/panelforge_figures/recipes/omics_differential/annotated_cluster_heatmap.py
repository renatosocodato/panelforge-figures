"""Annotated cluster heatmap — genes × samples with row/col condition strips."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class ClusterHeatmapInput(RecipeContract):
    gene_names: list[str] = Field(...)
    sample_names: list[str] = Field(...)
    expression_matrix: list[list[float]] = Field(
        ..., description="z-scored expression; rows=genes, cols=samples"
    )
    sample_conditions: list[str] = Field(..., description="condition per sample")
    title: str = "Annotated cluster heatmap"


def _demo() -> ClusterHeatmapInput:
    rng = np.random.default_rng(263)
    n_genes = 28
    genes = [f"GENE{i:02d}" for i in range(n_genes)]
    conditions = (["ctrl"] * 8 + ["treat"] * 8 + ["wash"] * 6)
    samples = [f"s{i:02d}" for i in range(len(conditions))]
    # Two gene modules: up in 'treat', down in 'treat'.
    mat = rng.normal(0, 0.6, (n_genes, len(conditions)))
    treat_mask = np.array([c == "treat" for c in conditions])
    mat[:12][:, treat_mask] += 1.8
    mat[12:22][:, treat_mask] -= 1.5
    return ClusterHeatmapInput(
        gene_names=genes,
        sample_names=samples,
        expression_matrix=mat.tolist(),
        sample_conditions=conditions,
    )


_META = RecipeMetadata(
    name="annotated_cluster_heatmap",
    modality="omics_differential",
    family=RecipeFamily.heatmap,
    answers_question="Which gene modules co-vary across samples, annotated by experimental condition?",
    required_fields=("gene_names", "sample_names", "expression_matrix",
                     "sample_conditions"),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("volcano_labeled_repelled",),
)


@register_recipe(metadata=_META, contract=ClusterHeatmapInput, demo_contract=_demo)
def render(contract: ClusterHeatmapInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.8))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    M = np.array(contract.expression_matrix, dtype=float)
    # Diverging cmap centered at 0 (z-score).
    vmax = max(abs(M.min()), abs(M.max()))
    im = ax.imshow(M, cmap=AESTHETIC.ratio_cmap or "RdBu_r",
                   vmin=-vmax, vmax=vmax, aspect="auto",
                   interpolation="nearest")

    ax.set_xticks(range(len(contract.sample_names)))
    ax.set_xticklabels(contract.sample_names, rotation=60, ha="right",
                       fontsize=5.6)
    # Row labels: just genes at every other row.
    step = max(1, len(contract.gene_names) // 12)
    tick_idx = list(range(0, len(contract.gene_names), step))
    ax.set_yticks(tick_idx)
    ax.set_yticklabels([contract.gene_names[i] for i in tick_idx],
                       fontsize=5.8)
    ax.set_title(contract.title, fontsize=9.0, pad=16)

    # Sample condition strip above axis.
    unique_conds = list(dict.fromkeys(contract.sample_conditions))
    cond_to_color = {c: palette[i % len(palette.colors)]
                     for i, c in enumerate(unique_conds)}
    strip_y = -0.06
    for j, c in enumerate(contract.sample_conditions):
        ax.annotate(
            "", xy=(j, strip_y + 0.02), xytext=(j, strip_y + 0.06),
            xycoords=("data", "axes fraction"),
            textcoords=("data", "axes fraction"),
            arrowprops=dict(arrowstyle="-", lw=4.5,
                            color=cond_to_color[c]),
        )

    # Legend of conditions.
    from matplotlib.lines import Line2D
    proxies = [
        Line2D([0], [0], marker="s", color="none",
               markerfacecolor=cond_to_color[c], markersize=7, label=c)
        for c in unique_conds
    ]
    ax.legend(handles=proxies, loc="upper center",
              bbox_to_anchor=(0.5, 1.12), ncol=len(unique_conds),
              fontsize=6.6, frameon=False, handlelength=1.0,
              columnspacing=1.2)

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.036, pad=0.04)
    cbar.set_label("z-score", fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.2)
    return ax
