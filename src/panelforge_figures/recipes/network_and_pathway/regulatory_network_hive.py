"""Regulatory hive plot — three axes (TFs / genes / enhancers) with curved edges."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class HiveInput(RecipeContract):
    axis_names: list[str] = Field(..., min_length=2, max_length=4,
                                  description="short axis labels, e.g. ['TF', 'Gene', 'Enhancer']")
    nodes_per_axis: dict[str, list[str]] = Field(
        ..., description="axis → node names"
    )
    edges: list[tuple[str, str, str, str]] = Field(
        ..., description="(axis_src, node_src, axis_dst, node_dst)"
    )
    edge_weights: list[float] = Field(default_factory=list,
                                      description="aligned with edges; optional")
    title: str = "Regulatory hive"


def _demo() -> HiveInput:
    rng = np.random.default_rng(331)
    axes = ["TF", "Gene", "Enhancer"]
    nodes_per_axis = {
        "TF": [f"TF{i}" for i in range(6)],
        "Gene": [f"G{i}" for i in range(8)],
        "Enhancer": [f"E{i}" for i in range(7)],
    }
    edges = []
    weights = []
    for _ in range(36):
        a, b = rng.choice(axes, size=2, replace=False)
        src = rng.choice(nodes_per_axis[a])
        dst = rng.choice(nodes_per_axis[b])
        edges.append((a, src, b, dst))
        weights.append(rng.uniform(0.2, 1.0))
    return HiveInput(
        axis_names=axes,
        nodes_per_axis=nodes_per_axis,
        edges=edges,
        edge_weights=weights,
    )


_META = RecipeMetadata(
    name="regulatory_network_hive",
    modality="network_and_pathway",
    family=RecipeFamily.scatter_collapse,
    answers_question="How do regulators connect to targets across categories, laid out along clean axes?",
    required_fields=("axis_names", "nodes_per_axis", "edges"),
    optional_fields=("edge_weights", "title"),
    file_format_hints=("graphml", "parquet"),
    alternatives_in_modality=("interaction_chord_diagram",),
)


@register_recipe(metadata=_META, contract=HiveInput, demo_contract=_demo)
def render(contract: HiveInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.8))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.2)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ("left", "bottom"):
        ax.spines[s].set_visible(False)
    ax.set_aspect("equal")

    axes = contract.axis_names
    n_axes = len(axes)
    # Axis directions equally spaced.
    thetas = np.linspace(np.pi / 2, np.pi / 2 + 2 * np.pi,
                          n_axes, endpoint=False)

    # Assign node positions along each axis.
    node_positions: dict[tuple[str, str], tuple[float, float]] = {}
    axis_colors = {}
    for ai, (a, theta) in enumerate(zip(axes, thetas)):
        color = palette[ai % len(palette.colors)]
        axis_colors[a] = color
        nodes = contract.nodes_per_axis[a]
        rs = np.linspace(0.2, 1.0, max(len(nodes), 1))
        for node, r in zip(nodes, rs):
            xp = r * np.cos(theta)
            yp = r * np.sin(theta)
            node_positions[(a, node)] = (xp, yp)
        # Axis line.
        ax.plot([0, np.cos(theta)], [0, np.sin(theta)],
                color=color, lw=1.1, zorder=3)
        # Axis label.
        ax.text(1.05 * np.cos(theta), 1.05 * np.sin(theta), a,
                color=color, ha="center", va="center", fontsize=7.4,
                bbox=dict(boxstyle="round,pad=0.14", fc="white",
                          ec="none", alpha=0.95),
                zorder=5)

    # Edges — curved Bezier-ish.
    max_w = max(contract.edge_weights) if contract.edge_weights else 1.0
    for i, (a_src, s_node, a_dst, d_node) in enumerate(contract.edges):
        if (a_src, s_node) not in node_positions or (a_dst, d_node) not in node_positions:
            continue
        x0, y0 = node_positions[(a_src, s_node)]
        x1, y1 = node_positions[(a_dst, d_node)]
        w = (contract.edge_weights[i] if i < len(contract.edge_weights) else 0.6) / max_w
        # Simple arc via connectionstyle.
        ax.annotate(
            "", xy=(x1, y1), xytext=(x0, y0),
            arrowprops=dict(
                arrowstyle="-", color="#444444",
                alpha=0.35 + 0.45 * w,
                lw=0.6 + 0.8 * w,
                connectionstyle="arc3,rad=0.18",
            ),
            zorder=2,
        )

    # Node dots.
    for (a, _name), (xp, yp) in node_positions.items():
        ax.scatter([xp], [yp], s=22, color=axis_colors[a],
                   edgecolor="white", linewidth=0.6, zorder=4)

    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.text(0.98, 0.02,
            f"{sum(len(v) for v in contract.nodes_per_axis.values())} nodes   "
            f"{len(contract.edges)} edges",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6.4, color="#444444",
            bbox=dict(boxstyle="round,pad=0.18", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)
    _ = smart_fmt
    return ax
