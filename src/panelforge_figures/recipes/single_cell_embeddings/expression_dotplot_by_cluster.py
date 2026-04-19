"""Expression dotplot — genes × clusters matrix, dot size ∝ %cells expressing, color ∝ mean."""

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


class ExpressionDotplotInput(RecipeContract):
    clusters: list[str]
    genes: list[str]
    mean_expression: list[list[float]] = Field(
        ..., description="mean[g][c] = mean expression of gene g in cluster c"
    )
    pct_expressing: list[list[float]] = Field(
        ..., description="pct[g][c] in [0, 1]"
    )
    title: str = "Expression dotplot"


def _demo() -> ExpressionDotplotInput:
    rng = np.random.default_rng(313)
    clusters = ["homeostatic", "surveillant", "activated", "DAM", "proliferative"]
    genes = ["P2ry12", "Tmem119", "Cx3cr1", "Itgax", "Cd74",
             "H2-Aa", "Cst7", "Apoe", "Trem2", "Ki67", "Top2a", "Mki67"]
    G, C = len(genes), len(clusters)
    mean_expr = rng.uniform(0, 1, (G, C)) ** 2
    pct = rng.uniform(0, 1, (G, C))
    # Make Ki67 / Top2a / Mki67 high in proliferative.
    for g in (9, 10, 11):
        mean_expr[g, 4] = 1.2
        pct[g, 4] = 0.85
    return ExpressionDotplotInput(
        clusters=clusters, genes=genes,
        mean_expression=mean_expr.tolist(),
        pct_expressing=pct.tolist(),
    )


_META = RecipeMetadata(
    name="expression_dotplot_by_cluster",
    modality="single_cell_embeddings",
    family=RecipeFamily.matrix,
    answers_question="Which genes are specifically expressed in which clusters, combining mean intensity and percent-expressing cells?",
    required_fields=("clusters", "genes", "mean_expression", "pct_expressing"),
    optional_fields=("title",),
    file_format_hints=("h5ad", "csv"),
    alternatives_in_modality=("umap_continuous_expression",),
)


@register_recipe(metadata=_META, contract=ExpressionDotplotInput, demo_contract=_demo)
def render(contract: ExpressionDotplotInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.6))
    AESTHETIC.apply_to_ax(ax)

    G = len(contract.genes)
    C = len(contract.clusters)
    mean_expr = np.array(contract.mean_expression, dtype=float)
    pct = np.array(contract.pct_expressing, dtype=float)

    xs = []
    ys = []
    sizes = []
    colors = []
    for gi in range(G):
        for ci in range(C):
            xs.append(ci)
            ys.append(gi)
            sizes.append(pct[gi, ci] * 110)
            colors.append(mean_expr[gi, ci])

    sc = ax.scatter(xs, ys, s=sizes, c=colors, cmap=AESTHETIC.continuous_cmap,
                    edgecolor="white", linewidth=0.4, alpha=0.92, zorder=3)

    ax.set_xticks(range(C))
    ax.set_xticklabels(contract.clusters, rotation=30, ha="right", fontsize=6.8)
    ax.set_yticks(range(G))
    ax.set_yticklabels(contract.genes, fontsize=6.6)
    ax.invert_yaxis()
    ax.set_title(
        f"{contract.title}  ·  {G} genes × {C} clusters,  "
        f"max mean = {smart_fmt(float(mean_expr.max()))}",
        fontsize=8.4, pad=4,
    )

    cbar = ax.figure.colorbar(sc, ax=ax, fraction=0.03, pad=0.04)
    cbar.set_label("mean expr", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)

    # Size legend.
    from matplotlib.lines import Line2D
    size_vals = [0.25, 0.5, 1.0]
    proxies = [
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor="#888888", markeredgecolor="white",
               markersize=np.sqrt(v * 110), label=f"{int(100 * v)}%")
        for v in size_vals
    ]
    ax.legend(handles=proxies,
              loc="center left", bbox_to_anchor=(1.18, 0.5),
              fontsize=6.2, frameon=False, handlelength=1.0,
              title="% cells", title_fontsize=6.4)

    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
