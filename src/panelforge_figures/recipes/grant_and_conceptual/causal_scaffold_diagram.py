"""Causal scaffold diagram — column-organized DAG with cross-column edges.

Used to depict a multi-stage scaffold from upstream factors → mediating state →
downstream phenotype. Each node is placed on a column × row grid; edges are
drawn from box-edge to box-edge so arrows never pierce node text.

Generic three-column scaffold (geometry → polymer state → protrusion
phenotype is one example layout) — captured here so the same diagram
becomes recipe-bound, reproducible, and audit-discoverable across projects.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class ScaffoldNode(RecipeContract):
    label: str
    column: int = Field(ge=0, le=4, description="0-indexed column (left → right)")
    row: int = Field(ge=0, le=5, description="0-indexed row (top → bottom)")
    kind: Literal["upstream", "mediator", "phenotype", "annotation"] = "mediator"


class ScaffoldEdge(RecipeContract):
    src: str = Field(description="Source node label")
    dst: str = Field(description="Destination node label")
    color: str = Field(default="#7b8fa3", description="Hex color for the edge arrow")
    weight: float = Field(default=1.0, ge=0.1, le=4.0, description="Line width multiplier")
    style: Literal["solid", "dashed"] = "solid"


class CausalScaffoldInput(RecipeContract):
    nodes: list[ScaffoldNode] = Field(min_length=2)
    edges: list[ScaffoldEdge] = Field(min_length=1)
    column_labels: tuple[str, str, str] | None = Field(
        default=None,
        description="Optional column-header strings; if None, columns are unlabeled",
    )
    title: str = "Causal scaffold"
    footer: str = ""
    show_column_lanes: bool = Field(default=False, description="Light vertical band per column")


def _demo() -> CausalScaffoldInput:
    return CausalScaffoldInput(
        nodes=[
            ScaffoldNode(label="Cell shape", column=0, row=0, kind="upstream"),
            ScaffoldNode(label="Cortex width", column=0, row=2, kind="upstream"),
            ScaffoldNode(label="Confinement", column=0, row=4, kind="upstream"),
            ScaffoldNode(label="MT alignment", column=1, row=1, kind="mediator"),
            ScaffoldNode(label="Lp invariance", column=1, row=3, kind="mediator"),
            ScaffoldNode(label="Buckling cascade", column=2, row=0, kind="phenotype"),
            ScaffoldNode(label=r"Stand-off $\uparrow$ (LI)", column=2, row=2, kind="phenotype"),
            ScaffoldNode(label="Protrusion drift", column=2, row=4, kind="phenotype"),
        ],
        edges=[
            ScaffoldEdge(src="Cell shape", dst="MT alignment", color="#7b8fa3"),
            ScaffoldEdge(src="Cortex width", dst="MT alignment", color="#7b8fa3"),
            ScaffoldEdge(src="Cortex width", dst="Lp invariance", color="#9c9c9c"),
            ScaffoldEdge(src="Confinement", dst="Lp invariance", color="#9c9c9c"),
            ScaffoldEdge(src="MT alignment", dst="Buckling cascade", color="#c0392b"),
            ScaffoldEdge(src="MT alignment", dst=r"Stand-off $\uparrow$ (LI)", color="#c0392b"),
            ScaffoldEdge(src="Lp invariance", dst=r"Stand-off $\uparrow$ (LI)", color="#1f6f8b"),
            ScaffoldEdge(src="Confinement", dst="Protrusion drift", color="#666666"),
        ],
        column_labels=("Geometry", "Polymer state", "Phenotype"),
        title=r"Causal scaffold (geometry $\rightarrow$ polymer state $\rightarrow$ protrusion phenotype)",
        footer="Cross-sectional snapshot; arrows = scaffolded co-occurrence, not causal direction",
    )


_META = RecipeMetadata(
    name="causal_scaffold_diagram",
    modality="grant_and_conceptual",
    family=RecipeFamily.flow,
    answers_question="How are upstream factors, mediators, and phenotypes organized into a multi-stage scaffold?",
    required_fields=("nodes", "edges"),
    optional_fields=("column_labels", "title", "footer", "show_column_lanes"),
    file_format_hints=("yaml", "toml", "json"),
    alternatives_in_modality=(
        "hypothesis_diagram",
        "methods_pipeline_flow",
        "narrative_cascade_river_with_xrefs",
    ),
)


_NODE_FILL = {
    "upstream":   "#e3ecf3",
    "mediator":   "#eef2f6",
    "phenotype":  "#f5ece4",
    "annotation": "#f7f7f7",
}
_NODE_EDGE = {
    "upstream":   "#5b8aa4",
    "mediator":   "#5b8aa4",
    "phenotype":  "#b4572a",
    "annotation": "#bbbbbb",
}


@register_recipe(metadata=_META, contract=CausalScaffoldInput, demo_contract=_demo)
def render(contract: CausalScaffoldInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(8.5, 5.0))
    AESTHETIC.apply_to_ax(ax)
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(0.02, 0.97)
    ax.axis("off")

    # Layout: 3 columns (or up to 5), N rows per column (max row across all nodes).
    nodes = list(contract.nodes)
    max_col = max(n.column for n in nodes)
    max_row = max(n.row for n in nodes)
    n_cols = max_col + 1
    n_rows = max_row + 1

    col_x = [0.06 + i * (0.94 / max(1, n_cols - 1) - 0.04 if n_cols > 1 else 0)
             for i in range(n_cols)]
    # Recompute col_x with even spacing 0.06 → 0.94 across n_cols
    if n_cols == 1:
        col_x = [0.50]
    elif n_cols == 2:
        col_x = [0.20, 0.80]
    elif n_cols == 3:
        col_x = [0.10, 0.45, 0.82]
    elif n_cols == 4:
        col_x = [0.08, 0.34, 0.62, 0.90]
    else:
        col_x = [0.06 + i * (0.88 / (n_cols - 1)) for i in range(n_cols)]

    row_y = [0.86 - i * (0.74 / max(1, n_rows - 1)) for i in range(n_rows)] \
        if n_rows > 1 else [0.50]

    # Optional column-lane shading
    if contract.show_column_lanes and n_cols > 1:
        lane_w = (col_x[1] - col_x[0]) * 0.85 if n_cols > 1 else 0.20
        for i, cx in enumerate(col_x):
            ax.axvspan(cx - lane_w / 2, cx + lane_w / 2,
                       color=("#f4f6f8" if i % 2 == 0 else "#fafbfc"),
                       alpha=0.55, zorder=0)

    # Column-header labels
    if contract.column_labels:
        for i, lbl in enumerate(contract.column_labels[:n_cols]):
            ax.text(col_x[i], 0.95, lbl,
                    ha="center", va="bottom", fontsize=9.6, fontweight="bold",
                    color="#2c3e50")

    # Position lookup for edge resolution
    pos = {n.label: (col_x[n.column], row_y[n.row]) for n in nodes}

    # Draw nodes
    # Explicit FancyBboxPatch per node so the patch count is queryable for
    # downstream consumers (flow-family integrity / patch-counters), and so
    # the box geometry is visible at hit-test time without forcing a draw.
    import matplotlib.patches as mpatches
    for n in nodes:
        x, y = pos[n.label]
        fill_color = _NODE_FILL.get(n.kind, "#eef2f6")
        edge_color = _NODE_EDGE.get(n.kind, "#5b8aa4")
        ax.add_patch(mpatches.FancyBboxPatch(
            (x - 0.07, y - 0.025), 0.14, 0.05,
            boxstyle="round,pad=0.005",
            fc=fill_color, ec=edge_color, lw=1.2,
            zorder=9,
        ))
        ax.text(x, y, n.label,
                ha="center", va="center", fontsize=9.6,
                bbox=dict(
                    boxstyle="round,pad=0.45",
                    fc=fill_color,
                    ec=edge_color,
                    lw=1.2,
                ),
                zorder=10)

    # Edge offset: arrows start/end OUTSIDE the node boxes so arrowheads
    # land at visible box edges, never piercing node text.
    OFFSET = 0.10

    name_to_node = {n.label: n for n in nodes}
    for e in contract.edges:
        if e.src not in pos or e.dst not in pos:
            continue
        x0, y0 = pos[e.src]
        x1, y1 = pos[e.dst]
        col_src = name_to_node[e.src].column
        col_dst = name_to_node[e.dst].column
        # Horizontal offsets per column delta
        if col_dst > col_src:
            sx, ex = OFFSET, -OFFSET
        elif col_dst < col_src:
            sx, ex = -OFFSET, OFFSET
        else:
            sx, ex = 0.0, 0.0
        linestyle = "--" if e.style == "dashed" else "-"
        ax.annotate(
            "",
            xy=(x1 + ex, y1),
            xytext=(x0 + sx, y0),
            arrowprops=dict(
                arrowstyle="->",
                color=e.color,
                lw=1.4 * e.weight,
                linestyle=linestyle,
                alpha=0.85,
                shrinkA=0, shrinkB=0,
            ),
            zorder=5,
        )

    if contract.title:
        ax.set_title(contract.title, fontsize=9.6, color="#2c3e50",
                     loc="center", pad=8)
    if contract.footer:
        ax.text(0.5, 0.005, contract.footer,
                ha="center", va="bottom", fontsize=8.4, color="#888",
                transform=ax.transAxes)

    return ax
