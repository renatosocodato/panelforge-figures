"""Sobol interaction *network* — graph view of pairwise Sᵢⱼ.

Same data as `interaction_matrix_sobol` (pairwise Sᵢⱼ), different
visual grammar: nodes sized by total-order Sᵀ if provided, edges
colour + width-coded by Sᵢⱼ, circular layout so edge structure is
legible. Reveals interaction clusters and hubs that a heatmap
collapses into rows.
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


class InteractionNetworkInput(RecipeContract):
    parameter_names: list[str] = Field(..., min_length=3)
    S2: list[list[float]] = Field(
        ..., description="symmetric parameter × parameter matrix"
    )
    ST: list[float] | None = Field(
        None, description="total-order index per parameter (sets node size)"
    )
    edge_threshold: float = 0.02
    title: str = "Interaction network (Sobol)"


def _demo() -> InteractionNetworkInput:
    rng = np.random.default_rng(913)
    names = ["k_on", "k_off", "V_max", "Km", "D", "alpha", "beta"]
    n = len(names)
    M = np.abs(rng.normal(0.008, 0.012, (n, n)))
    M = (M + M.T) / 2
    np.fill_diagonal(M, 0)
    # Inject hub + cluster structure.
    M[0, 3] = M[3, 0] = 0.22      # k_on–Km — strong
    M[0, 2] = M[2, 0] = 0.14      # k_on–V_max
    M[2, 3] = M[3, 2] = 0.12
    M[1, 5] = M[5, 1] = 0.08
    M[5, 6] = M[6, 5] = 0.06
    st = np.array([0.62, 0.18, 0.42, 0.38, 0.04, 0.22, 0.12])
    return InteractionNetworkInput(
        parameter_names=names, S2=M.tolist(), ST=st.tolist(),
    )


_META = RecipeMetadata(
    name="interaction_network_sobol",
    modality="sensitivity_analysis",
    family=RecipeFamily.conceptual,
    answers_question=(
        "As a graph, which parameters form the strongest interaction "
        "clusters and which are hubs?"
    ),
    required_fields=("parameter_names", "S2"),
    optional_fields=("ST", "edge_threshold", "title"),
    file_format_hints=("parquet", "npz"),
    alternatives_in_modality=("interaction_matrix_sobol",),
)


@register_recipe(
    metadata=_META,
    contract=InteractionNetworkInput,
    demo_contract=_demo,
)
def render(contract: InteractionNetworkInput, ax=None, **_):
    import matplotlib as mpl
    import matplotlib.patches as mpatches

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 4.6))
    AESTHETIC.apply_to_ax(ax)

    M = np.asarray(contract.S2, float)
    n = M.shape[0]
    names = contract.parameter_names
    cmap = mpl.colormaps[AESTHETIC.continuous_cmap]

    # Circular layout.
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False) + np.pi / 2
    R = 1.0
    pos = np.stack([R * np.cos(theta), R * np.sin(theta)], axis=1)

    # Edges above threshold.
    edges = []
    for i in range(n):
        for j in range(i):
            v = M[i, j]
            if v >= contract.edge_threshold:
                edges.append((i, j, v))
    edges.sort(key=lambda e: e[2])  # draw small → large so big edges are on top
    v_hi = max((v for _, _, v in edges), default=contract.edge_threshold)

    for i, j, v in edges:
        color = cmap(0.30 + 0.65 * v / max(v_hi, 1e-9))
        lw = 0.8 + 3.0 * v / max(v_hi, 1e-9)
        ax.plot([pos[i, 0], pos[j, 0]], [pos[i, 1], pos[j, 1]],
                color=color, lw=lw, alpha=0.85, zorder=3)

    # Node size from ST if available.
    if contract.ST is not None:
        st = np.asarray(contract.ST, float)
        st_norm = (st - st.min()) / max(st.max() - st.min(), 1e-9)
        radii = 0.07 + 0.10 * st_norm
    else:
        radii = np.full(n, 0.09)

    for k, name in enumerate(names):
        x, y = pos[k]
        node_color = (cmap(0.25 + 0.6 * st_norm[k])
                      if contract.ST is not None else "#1F77B4")
        ax.add_patch(mpatches.Circle(
            (x, y), radii[k],
            facecolor=node_color, edgecolor="white", linewidth=1.0,
            zorder=5,
        ))
        # Label slightly outside the circle, rotated-radially away.
        label_r = R + radii[k] + 0.06
        lx, ly = label_r * np.cos(theta[k]), label_r * np.sin(theta[k])
        ha = ("center" if abs(np.cos(theta[k])) < 0.3
              else ("left" if np.cos(theta[k]) > 0 else "right"))
        va = ("center" if abs(np.sin(theta[k])) < 0.3
              else ("bottom" if np.sin(theta[k]) > 0 else "top"))
        ax.text(lx, ly, name, ha=ha, va=va,
                fontsize=7.4, color="#111111", zorder=6)

    # Edge-weight colorbar legend (small, floating).
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize
    norm = Normalize(vmin=contract.edge_threshold, vmax=max(v_hi, 1e-9))
    sm = ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cbar = ax.figure.colorbar(sm, ax=ax, fraction=0.035, pad=0.04,
                              shrink=0.45)
    cbar.set_label("S₂", fontsize=7.0)
    cbar.ax.tick_params(labelsize=6.4)

    # Top-edge callout.
    edges_desc = sorted(edges, key=lambda e: -e[2])[:3]
    top = ", ".join(
        f"{names[i]}×{names[j]}={smart_fmt(v)}" for i, j, v in edges_desc
    ) if edges_desc else "No edges above threshold."

    ax.set_xlim(-R - 0.42, R + 0.42)
    ax.set_ylim(-R - 0.42, R + 0.42)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    fig = ax.figure
    fig.text(
        0.5, -0.10,
        f"top edges: {top}",
        ha="center", va="top", fontsize=6.8, color="#333333",
        transform=ax.transAxes,
        bbox=dict(boxstyle="round,pad=0.24", fc="white",
                  ec=AESTHETIC.annotation_style.callout_accent, lw=0.5),
    )
    return ax
