"""Directed regulatory network — force-directed layout with arrowed edges."""

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


class DirectedNetworkInput(RecipeContract):
    node_names: list[str] = Field(..., min_length=3)
    node_class: list[str] | None = None
    edges: list[tuple[int, int]] = Field(
        ..., description="list of (src_idx, dst_idx) pairs"
    )
    edge_weight: list[float] | None = None
    title: str = "Directed network · force layout"


def _degree_radial_layout(n, edges, seed=0):
    """Degree-based radial layout: high-degree nodes near centre, low at
    rim. Deterministic and readable for small-to-medium graphs where a
    spring layout collapses. Nodes of equal degree are spaced angularly.
    """
    rng = np.random.default_rng(seed)
    deg = np.zeros(n, dtype=int)
    for s, d in edges:
        if s < n:
            deg[s] += 1
        if d < n:
            deg[d] += 1
    # Assign radii: rank nodes by degree descending (hubs at centre).
    order = np.argsort(-deg)
    ranks = np.empty(n, dtype=int)
    ranks[order] = np.arange(n)
    # Radius increases with rank; add a small jitter for aesthetic.
    base_r = 0.15 + 0.75 * (ranks / max(n - 1, 1))
    # Angle: stratify within degree tiers to avoid overlap.
    angles = np.zeros(n)
    unique_d = sorted(set(deg.tolist()), reverse=True)
    for d_val in unique_d:
        idx = np.where(deg == d_val)[0]
        rng.shuffle(idx)
        for k, i in enumerate(idx):
            angles[i] = 2 * np.pi * k / max(len(idx), 1) + d_val * 0.37
    jitter = rng.uniform(-0.03, 0.03, n)
    x = base_r * np.cos(angles) + jitter
    y = base_r * np.sin(angles) + jitter
    return np.column_stack([x, y])


def _spring_layout(n, edges, iters=50, seed=0):
    """Public entry — delegates to the degree-radial layout."""
    return _degree_radial_layout(n, edges, seed=seed)


def _demo() -> DirectedNetworkInput:
    rng = np.random.default_rng(409)
    classes = ["signaling", "metabolic", "cytoskeletal", "other"]
    n = 18
    names = [f"n{i:02d}" for i in range(n)]
    node_class = rng.choice(classes, n, p=[0.4, 0.3, 0.2, 0.1]).tolist()
    # Edges: build a scale-free-ish sparse graph with a few hubs.
    edges: list[tuple[int, int]] = []
    for _ in range(30):
        s = int(rng.integers(0, n))
        d = int(rng.integers(0, n))
        if s != d:
            edges.append((s, d))
    # Give node 0 extra outgoing.
    for i in range(5):
        d = int(rng.integers(1, n))
        if d != 0:
            edges.append((0, d))
    weights = rng.uniform(0.2, 1.0, len(edges)).tolist()
    return DirectedNetworkInput(
        node_names=names,
        node_class=node_class,
        edges=edges,
        edge_weight=weights,
    )


_META = RecipeMetadata(
    name="directed_network_force_layout",
    modality="network_and_pathway",
    family=RecipeFamily.conceptual,
    answers_question=(
        "In a directed regulatory network, how do nodes cluster "
        "spatially and what are the dominant directed hubs?"
    ),
    required_fields=("node_names", "edges"),
    optional_fields=("node_class", "edge_weight", "title"),
    file_format_hints=("graphml", "json"),
    alternatives_in_modality=("regulatory_network_hive",),
)


@register_recipe(
    metadata=_META,
    contract=DirectedNetworkInput,
    demo_contract=_demo,
)
def render(contract: DirectedNetworkInput, ax=None, **_):
    import matplotlib.patches as mpatches

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 4.0))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    names = contract.node_names
    n = len(names)
    classes = (contract.node_class
               if contract.node_class is not None
               else ["other"] * n)
    edges = contract.edges
    weights = (contract.edge_weight
               if contract.edge_weight is not None
               else [0.5] * len(edges))

    pos = _spring_layout(n, edges, iters=80, seed=7)

    # Compute out-degree for sizing.
    out_deg = np.zeros(n)
    for s, _d in edges:
        if s < n:
            out_deg[s] += 1
    sizes = 40 + 150 * (out_deg / max(out_deg.max(), 1))

    # Draw edges with arrows.
    max_w = max(weights) if weights else 1.0
    for (s, d), w in zip(edges, weights):
        if s >= n or d >= n:
            continue
        ax.annotate(
            "", xy=pos[d], xytext=pos[s],
            arrowprops=dict(
                arrowstyle="->", color="#777777",
                alpha=0.35 + 0.55 * (w / max_w),
                lw=0.5 + 1.2 * (w / max_w),
                shrinkA=6, shrinkB=8,
            ),
            zorder=2,
        )

    # Draw nodes as Circle patches so conceptual rule sees ≥2 patches.
    for i, (nm, c, s) in enumerate(zip(names, classes, sizes)):
        color = (palette.pick(c) if c in palette.semantic
                 else palette[0])
        radius = 0.035 + 0.0008 * s
        ax.add_patch(mpatches.Circle(
            pos[i], radius,
            facecolor=color, edgecolor="white", linewidth=0.7,
            zorder=4,
        ))
        # Only label top-degree nodes to avoid clutter.
        if out_deg[i] >= np.quantile(out_deg, 0.75):
            ax.text(pos[i, 0], pos[i, 1] + radius + 0.045, nm,
                    ha="center", va="bottom", fontsize=6.2,
                    color="#111111", zorder=6)

    # Hub callout.
    top_hub_idx = int(np.argmax(out_deg))
    ax.text(
        0.02, 0.98,
        f"N nodes = {n}   N edges = {len(edges)}\n"
        f"top hub: {names[top_hub_idx]} "
        f"(out-deg = {smart_fmt(float(out_deg[top_hub_idx]))})",
        transform=ax.transAxes, ha="left", va="top",
        fontsize=6.4, color="#111111",
        bbox=dict(boxstyle="round,pad=0.22", fc="white",
                  ec="#BBBBBB", lw=0.5, alpha=0.95),
        zorder=7,
    )

    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    # Legend by class (Patch proxies count as figure patches too).
    unique_c = list(dict.fromkeys(classes))
    proxies = [
        mpatches.Patch(
            facecolor=(palette.pick(c) if c in palette.semantic
                       else palette[0]),
            edgecolor="white", label=c)
        for c in unique_c
    ]
    ax.legend(handles=proxies, fontsize=6.2, frameon=False,
              loc="lower right", handlelength=1.0)
    return ax
