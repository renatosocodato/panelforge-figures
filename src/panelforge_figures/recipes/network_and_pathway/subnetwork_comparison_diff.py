"""Differential subnetwork — per-edge Δ-weight between conditions."""

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


class DiffSubnetworkInput(RecipeContract):
    node_names: list[str] = Field(..., min_length=4)
    edges: list[tuple[int, int]] = Field(
        ..., description="list of (src_idx, dst_idx) pairs"
    )
    delta_weight: list[float] = Field(
        ..., description="per-edge Δ-weight (post − pre), same length as edges"
    )
    condition_a: str = "pre"
    condition_b: str = "post"
    title: str = "Differential subnetwork"


def _spring_layout(n, edges, iters=60, seed=0):
    rng = np.random.default_rng(seed)
    pos = rng.uniform(-1, 1, (n, 2))
    k = np.sqrt(1.0 / max(n, 1))
    for _ in range(iters):
        disp = np.zeros_like(pos)
        for i in range(n):
            delta = pos[i] - pos
            dist = np.linalg.norm(delta, axis=1)
            dist = np.where(dist < 1e-3, 1e-3, dist)
            force = k * k / dist[:, None]
            disp[i] += (delta / dist[:, None] * force).sum(axis=0)
        for s, d in edges:
            if s >= n or d >= n:
                continue
            delta = pos[s] - pos[d]
            dist = np.linalg.norm(delta) + 1e-9
            force = dist * dist / k
            disp[s] -= delta / dist * force * 0.5
            disp[d] += delta / dist * force * 0.5
        step = np.minimum(np.linalg.norm(disp, axis=1, keepdims=True), 0.1)
        pos += disp / (np.linalg.norm(disp, axis=1, keepdims=True) + 1e-9) * step
    pos -= pos.mean(axis=0)
    scale = max(np.abs(pos).max(), 1e-6)
    return pos / scale * 0.9


def _demo() -> DiffSubnetworkInput:
    rng = np.random.default_rng(1117)
    n = 16
    names = [f"n{i:02d}" for i in range(n)]
    edges: list[tuple[int, int]] = []
    for _ in range(28):
        s = int(rng.integers(0, n))
        d = int(rng.integers(0, n))
        if s != d:
            edges.append((s, d))
    delta = rng.normal(0, 0.4, len(edges)).tolist()
    # Inject a few strong gains / losses.
    for idx in rng.choice(len(edges), 6, replace=False):
        delta[idx] = float(rng.choice([-1.0, 1.0]) * rng.uniform(0.8, 1.5))
    return DiffSubnetworkInput(
        node_names=names,
        edges=edges,
        delta_weight=delta,
        condition_a="control",
        condition_b="LPS",
    )


_META = RecipeMetadata(
    name="subnetwork_comparison_diff",
    modality="network_and_pathway",
    family=RecipeFamily.conceptual,
    answers_question=(
        "Between conditions, which edges gain / lose weight "
        "(differential subnetwork)?"
    ),
    required_fields=("node_names", "edges", "delta_weight"),
    optional_fields=("condition_a", "condition_b", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("regulatory_network_hive",),
)


@register_recipe(
    metadata=_META,
    contract=DiffSubnetworkInput,
    demo_contract=_demo,
)
def render(contract: DiffSubnetworkInput, ax=None, **_):
    import matplotlib.patches as mpatches

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 4.0))
    AESTHETIC.apply_to_ax(ax)

    names = contract.node_names
    n = len(names)
    edges = contract.edges
    delta = np.asarray(contract.delta_weight, float)
    pos = _spring_layout(n, edges, iters=80, seed=17)

    # Node size by total |Δ| incident.
    deg_mag = np.zeros(n)
    for (s, d), dw in zip(edges, delta):
        if s < n:
            deg_mag[s] += abs(dw)
        if d < n:
            deg_mag[d] += abs(dw)
    sizes = 30 + 110 * (deg_mag / max(deg_mag.max(), 1e-6))

    gain_color = "#2E7D32"
    loss_color = "#C62828"
    max_abs = float(max(abs(delta).max(), 1e-6))

    # Edges — colour by sign, lw by |Δ|.
    for (s, d), dw in zip(edges, delta):
        if s >= n or d >= n:
            continue
        color = gain_color if dw >= 0 else loss_color
        lw = 0.4 + 1.8 * (abs(dw) / max_abs)
        ax.plot([pos[s, 0], pos[d, 0]], [pos[s, 1], pos[d, 1]],
                color=color, alpha=0.65, lw=lw, zorder=2)

    # Nodes as Circle patches.
    for i, nm in enumerate(names):
        radius = 0.03 + 0.0008 * sizes[i]
        ax.add_patch(mpatches.Circle(
            pos[i], radius,
            facecolor="#455A64", edgecolor="white", linewidth=0.7,
            zorder=4,
        ))
        if sizes[i] >= np.quantile(sizes, 0.7):
            ax.text(pos[i, 0], pos[i, 1] + radius + 0.02, nm,
                    ha="center", va="bottom", fontsize=6.2,
                    color="#111111", zorder=5)

    n_gain = int((delta > 0.1).sum())
    n_loss = int((delta < -0.1).sum())
    ax.text(
        0.02, 0.98,
        f"{contract.condition_a} -> {contract.condition_b}\n"
        f"gains: {n_gain}   losses: {n_loss}   "
        f"max|Δ|={smart_fmt(max_abs)}",
        transform=ax.transAxes, ha="left", va="top",
        fontsize=6.4, color="#111111",
        bbox=dict(boxstyle="round,pad=0.22", fc="white",
                  ec="#BBBBBB", lw=0.5, alpha=0.95),
        zorder=7,
    )

    # Legend.
    proxies = [
        mpatches.Patch(facecolor=gain_color, edgecolor="white",
                       label="gain (Δ > 0)"),
        mpatches.Patch(facecolor=loss_color, edgecolor="white",
                       label="loss (Δ < 0)"),
    ]
    ax.legend(handles=proxies, fontsize=6.4, frameon=False,
              loc="lower right", handlelength=1.2)

    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    return ax
