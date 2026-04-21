"""PPI seed + first-neighbour expansion — two-shell layout."""

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


class PPISeedInput(RecipeContract):
    seed_names: list[str] = Field(..., min_length=3)
    expanded_names: list[str] = Field(..., min_length=3)
    edges: list[tuple[str, str]] = Field(
        ..., description="edges across seed + expanded shells"
    )
    title: str = "PPI seed expansion"


def _demo() -> PPISeedInput:
    rng = np.random.default_rng(613)
    seeds = [f"S{i}" for i in range(5)]
    expanded = [f"X{i:02d}" for i in range(16)]
    edges: list[tuple[str, str]] = []
    # Seeds form a clique-like core.
    for i, s in enumerate(seeds):
        for other in seeds[i + 1:]:
            if rng.random() < 0.7:
                edges.append((s, other))
    # Each expanded connects to 1-2 seeds.
    for x in expanded:
        k = int(rng.integers(1, 3))
        for s in rng.choice(seeds, size=k, replace=False):
            edges.append((s, x))
    # A few expanded-expanded edges.
    for _ in range(8):
        a, b = rng.choice(expanded, size=2, replace=False)
        edges.append((a, b))
    return PPISeedInput(
        seed_names=seeds,
        expanded_names=expanded,
        edges=edges,
    )


_META = RecipeMetadata(
    name="ppi_seed_expansion",
    modality="network_and_pathway",
    family=RecipeFamily.conceptual,
    answers_question=(
        "Starting from a seed gene set, what does the first-neighbour "
        "expansion look like?"
    ),
    required_fields=("seed_names", "expanded_names", "edges"),
    optional_fields=("title",),
    file_format_hints=("json", "graphml"),
    alternatives_in_modality=("regulatory_network_hive",),
)


@register_recipe(
    metadata=_META,
    contract=PPISeedInput,
    demo_contract=_demo,
)
def render(contract: PPISeedInput, ax=None, **_):
    import matplotlib.patches as mpatches

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 4.2))
    AESTHETIC.apply_to_ax(ax)

    seeds = contract.seed_names
    expanded = contract.expanded_names
    edges = contract.edges
    n_seed = len(seeds)
    n_exp = len(expanded)

    # Seed positions on a small inner circle; expanded on outer.
    r_seed = 0.35
    r_exp = 1.0
    theta_seed = np.linspace(0, 2 * np.pi, n_seed, endpoint=False) + np.pi / 2
    theta_exp = np.linspace(0, 2 * np.pi, n_exp, endpoint=False) + np.pi / 2

    pos: dict[str, tuple[float, float]] = {}
    for name, th in zip(seeds, theta_seed):
        pos[name] = (r_seed * np.cos(th), r_seed * np.sin(th))
    for name, th in zip(expanded, theta_exp):
        pos[name] = (r_exp * np.cos(th), r_exp * np.sin(th))

    seed_color = "#D32F2F"
    exp_color = "#1565C0"

    # Shell rings.
    ax.add_patch(mpatches.Circle(
        (0, 0), r_seed + 0.18,
        facecolor="#FFF3E0", edgecolor="#FFB74D", linewidth=0.6,
        alpha=0.35, zorder=1,
    ))
    ax.add_patch(mpatches.Circle(
        (0, 0), r_exp + 0.20,
        facecolor="#E3F2FD", edgecolor="#90CAF9", linewidth=0.4,
        alpha=0.20, zorder=0,
    ))

    # Edges — seed-seed darker, seed-expanded medium, exp-exp light.
    seed_set = set(seeds)
    for s, d in edges:
        if s not in pos or d not in pos:
            continue
        if s in seed_set and d in seed_set:
            col, alpha, lw = "#B71C1C", 0.75, 1.0
        elif (s in seed_set) ^ (d in seed_set):
            col, alpha, lw = "#555555", 0.45, 0.6
        else:
            col, alpha, lw = "#AAAAAA", 0.30, 0.4
        x0, y0 = pos[s]
        x1, y1 = pos[d]
        ax.plot([x0, x1], [y0, y1], color=col, alpha=alpha,
                lw=lw, zorder=2)

    # Seed nodes.
    for name in seeds:
        x, y = pos[name]
        ax.add_patch(mpatches.Circle(
            (x, y), 0.08,
            facecolor=seed_color, edgecolor="white", linewidth=1.0,
            zorder=5,
        ))
        ax.text(x, y, name, ha="center", va="center",
                fontsize=6.2, color="white", fontweight="bold", zorder=6)

    # Expanded nodes.
    for name in expanded:
        x, y = pos[name]
        ax.add_patch(mpatches.Circle(
            (x, y), 0.055,
            facecolor=exp_color, edgecolor="white", linewidth=0.6,
            alpha=0.80, zorder=4,
        ))
        # Label on the outer side of the ring.
        th = np.arctan2(y, x)
        label_r = r_exp + 0.13
        ax.text(label_r * np.cos(th), label_r * np.sin(th), name,
                ha="center", va="center", fontsize=5.8,
                color=exp_color, zorder=6)

    # Legend proxies.
    proxies = [
        mpatches.Patch(facecolor=seed_color, edgecolor="white",
                       label=f"seed (n={n_seed})"),
        mpatches.Patch(facecolor=exp_color, edgecolor="white",
                       label=f"expanded (n={n_exp})"),
    ]
    ax.legend(handles=proxies, fontsize=6.4, frameon=False,
              loc="lower center", bbox_to_anchor=(0.5, -0.04),
              ncols=2, handlelength=1.2)

    ax.set_xlim(-1.45, 1.45)
    ax.set_ylim(-1.45, 1.45)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)

    ax.set_title(
        f"{contract.title}  ·  {n_seed} seeds + {n_exp} expanded, "
        f"{smart_fmt(len(edges))} edges",
        fontsize=8.6, pad=4,
    )
    return ax
