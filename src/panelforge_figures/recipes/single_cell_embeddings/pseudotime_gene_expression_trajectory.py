"""Marker-gene expression curves along pseudotime.

For a set of marker genes, plots the smoothed mean ± CI expression
curve as a function of pseudotime. Distinct from
`umap_continuous_expression` (spatial view of one gene) and
`expression_dotplot_by_cluster` (discrete cluster x-axis).
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


class PseudotimeGeneInput(RecipeContract):
    pseudotime: list[float] = Field(..., min_length=3)
    gene_curves: dict[str, list[float]] = Field(
        ..., description="gene name → smoothed mean expression at each pseudotime"
    )
    gene_ci: dict[str, list[float]] | None = Field(
        None, description="gene name → CI (or SEM) at each pseudotime"
    )
    title: str = "Gene expression vs pseudotime"


def _demo() -> PseudotimeGeneInput:
    rng = np.random.default_rng(919)
    pt = np.linspace(0, 1, 60)
    # Early-, mid- and late-pseudotime genes.
    early = np.exp(-((pt - 0.1) / 0.15) ** 2) + rng.normal(0, 0.02, pt.size)
    mid = np.exp(-((pt - 0.5) / 0.18) ** 2) + rng.normal(0, 0.02, pt.size)
    late = np.exp(-((pt - 0.9) / 0.14) ** 2) + rng.normal(0, 0.02, pt.size)
    up = 0.2 + 0.8 * pt + rng.normal(0, 0.02, pt.size)
    return PseudotimeGeneInput(
        pseudotime=pt.tolist(),
        gene_curves={
            "P2ry12":  early.tolist(),
            "Cd74":    mid.tolist(),
            "Cst7":    late.tolist(),
            "Apoe":    up.tolist(),
        },
        gene_ci={
            g: (0.08 * np.ones(pt.size)).tolist()
            for g in ("P2ry12", "Cd74", "Cst7", "Apoe")
        },
    )


_META = RecipeMetadata(
    name="pseudotime_gene_expression_trajectory",
    modality="single_cell_embeddings",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question=(
        "How do marker genes' expression curves evolve along "
        "pseudotime?"
    ),
    required_fields=("pseudotime", "gene_curves"),
    optional_fields=("gene_ci", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("umap_continuous_expression",),
)


@register_recipe(
    metadata=_META,
    contract=PseudotimeGeneInput,
    demo_contract=_demo,
)
def render(contract: PseudotimeGeneInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.4))
    AESTHETIC.apply_to_ax(ax)

    pt = np.asarray(contract.pseudotime, float)
    colors = ["#1565C0", "#E65100", "#2E7D32", "#6A1B9A", "#C62828"]
    ci_dict = contract.gene_ci or {}

    for i, (gene, vals) in enumerate(contract.gene_curves.items()):
        v = np.asarray(vals, float)
        color = colors[i % len(colors)]
        ci = np.asarray(ci_dict.get(gene, []), float) if ci_dict else None
        if ci is not None and ci.size == v.size:
            ax.fill_between(pt, v - ci / 2, v + ci / 2,
                            color=color, alpha=0.18, linewidth=0, zorder=2)
        ax.plot(pt, v, color=color, lw=1.3, zorder=3, label=gene)
        # Peak pseudotime marker.
        pk = int(np.argmax(v))
        ax.scatter([pt[pk]], [v[pk]], s=22, color=color,
                   edgecolor="white", linewidth=0.6, zorder=4)

    ax.set_xlabel("pseudotime")
    ax.set_ylabel("expression (smoothed mean)")
    ax.set_xlim(pt.min(), pt.max())
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="center left",
              bbox_to_anchor=(1.02, 0.5), handlelength=1.6)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Peak-pseudotime ordering callout.
    peak_pt = {
        gene: float(pt[int(np.argmax(np.asarray(vals, float)))])
        for gene, vals in contract.gene_curves.items()
    }
    ordered = sorted(peak_pt.items(), key=lambda it: it[1])
    peak_str = "  ->  ".join(f"{g}({smart_fmt(p)})" for g, p in ordered)
    fig = ax.figure
    fig.text(
        0.5, -0.16,
        f"peak order: {peak_str}",
        ha="center", va="top", fontsize=6.4, color="#333333",
        transform=ax.transAxes,
        bbox=dict(boxstyle="round,pad=0.22", fc="white",
                  ec="#BBBBBB", lw=0.5, alpha=0.92),
    )
    return ax
