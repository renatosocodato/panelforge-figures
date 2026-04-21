"""KEGG-style enrichment overlay — schematic box-and-arrow nodes coloured by p-value."""

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


class KEGGNode(RecipeContract):
    name: str
    x: float
    y: float
    neg_log10_p: float = 0.0
    gene_count: int = 1


class KEGGOverlayInput(RecipeContract):
    nodes: list[KEGGNode] = Field(..., min_length=3)
    edges: list[tuple[str, str]] = Field(default_factory=list)
    pathway_name: str = "pathway"
    title: str = "KEGG enrichment overlay"


def _demo() -> KEGGOverlayInput:
    nodes = [
        KEGGNode(name="Receptor",  x=0.1, y=0.8, neg_log10_p=5.3, gene_count=8),
        KEGGNode(name="Adapter",   x=0.3, y=0.6, neg_log10_p=3.1, gene_count=4),
        KEGGNode(name="Kinase1",   x=0.5, y=0.7, neg_log10_p=4.8, gene_count=6),
        KEGGNode(name="Kinase2",   x=0.5, y=0.4, neg_log10_p=1.2, gene_count=2),
        KEGGNode(name="Phosphatase", x=0.7, y=0.6, neg_log10_p=0.4, gene_count=1),
        KEGGNode(name="TF",        x=0.85, y=0.45, neg_log10_p=6.1, gene_count=7),
        KEGGNode(name="Target",    x=0.85, y=0.2, neg_log10_p=2.9, gene_count=3),
    ]
    edges = [
        ("Receptor", "Adapter"),
        ("Adapter", "Kinase1"),
        ("Adapter", "Kinase2"),
        ("Kinase1", "Phosphatase"),
        ("Kinase2", "Phosphatase"),
        ("Phosphatase", "TF"),
        ("TF", "Target"),
    ]
    return KEGGOverlayInput(nodes=nodes, edges=edges,
                            pathway_name="MAPK (KEGG)")


_META = RecipeMetadata(
    name="kegg_overlay_enrichment",
    modality="network_and_pathway",
    family=RecipeFamily.conceptual,
    answers_question=(
        "For a candidate KEGG pathway, which nodes are enriched in "
        "my hit list?"
    ),
    required_fields=("nodes",),
    optional_fields=("edges", "pathway_name", "title"),
    file_format_hints=("json",),
    alternatives_in_modality=("pathway_flux_sankey_like",),
)


@register_recipe(
    metadata=_META,
    contract=KEGGOverlayInput,
    demo_contract=_demo,
)
def render(contract: KEGGOverlayInput, ax=None, **_):
    import matplotlib as mpl
    import matplotlib.patches as mpatches

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.6))
    AESTHETIC.apply_to_ax(ax)

    nodes = contract.nodes
    name_to_pos = {n.name: (n.x, n.y) for n in nodes}
    p_vals = np.asarray([n.neg_log10_p for n in nodes], float)
    gene_counts = np.asarray([n.gene_count for n in nodes], float)
    v_max = float(max(p_vals.max(), 1e-9))

    cmap = mpl.colormaps["magma"]

    # Edges first (beneath nodes).
    for src, dst in contract.edges:
        if src not in name_to_pos or dst not in name_to_pos:
            continue
        x0, y0 = name_to_pos[src]
        x1, y1 = name_to_pos[dst]
        ax.annotate(
            "", xy=(x1, y1), xytext=(x0, y0),
            arrowprops=dict(arrowstyle="->", color="#666666",
                            lw=0.8, shrinkA=14, shrinkB=14),
            zorder=2,
        )

    # Nodes as rounded boxes.
    max_count = max(gene_counts.max(), 1)
    for node, p, g in zip(nodes, p_vals, gene_counts):
        w = 0.08 + 0.08 * (g / max_count)
        h = 0.06
        color = cmap(0.25 + 0.65 * (p / v_max))
        ax.add_patch(mpatches.FancyBboxPatch(
            (node.x - w / 2, node.y - h / 2), w, h,
            boxstyle="round,pad=0.01",
            facecolor=color, edgecolor="#111111", linewidth=0.8,
            zorder=4,
        ))
        text_color = "white" if p > v_max * 0.5 else "#111111"
        ax.text(node.x, node.y, node.name, ha="center", va="center",
                fontsize=6.4, color=text_color, zorder=5)

    # Colorbar proxy.
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize
    sm = ScalarMappable(norm=Normalize(vmin=0, vmax=v_max), cmap=cmap)
    sm.set_array([])
    cbar = ax.figure.colorbar(sm, ax=ax, fraction=0.04, pad=0.03)
    cbar.set_label(r"$-\log_{10}$ p$_{adj}$", fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    # Top-enriched node callout.
    top_i = int(np.argmax(p_vals))
    ax.text(
        0.02, 0.98,
        f"pathway: {contract.pathway_name}\n"
        f"top node: {nodes[top_i].name}  "
        f"(p={smart_fmt(float(p_vals[top_i]))}, "
        f"n={int(gene_counts[top_i])})",
        transform=ax.transAxes, ha="left", va="top",
        fontsize=6.4, color="#111111",
        bbox=dict(boxstyle="round,pad=0.22", fc="white",
                  ec="#BBBBBB", lw=0.5, alpha=0.95),
        zorder=6,
    )

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    return ax
