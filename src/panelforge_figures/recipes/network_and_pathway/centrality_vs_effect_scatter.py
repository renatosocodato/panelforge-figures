"""Centrality × effect-size scatter — do hubs have the biggest effects?"""

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


class CentralityEffectInput(RecipeContract):
    node_names: list[str] = Field(..., min_length=5)
    centrality: list[float] = Field(...)
    effect_size: list[float] = Field(...)
    p_value: list[float] | None = None
    title: str = "Centrality vs effect size"


def _demo() -> CentralityEffectInput:
    rng = np.random.default_rng(1013)
    n = 120
    names = [f"g{i:04d}" for i in range(n)]
    cent = 10 ** rng.uniform(0, 2.2, n)
    # Weak positive correlation with extras at top-right.
    effect = 0.4 * np.log10(cent) + rng.normal(0, 0.3, n)
    # Inject a cluster of high-effect hubs.
    top = rng.choice(n, 6, replace=False)
    effect[top] += rng.uniform(0.8, 1.4, 6)
    p = rng.uniform(0.001, 0.5, n)
    return CentralityEffectInput(
        node_names=names,
        centrality=cent.tolist(),
        effect_size=effect.tolist(),
        p_value=p.tolist(),
    )


_META = RecipeMetadata(
    name="centrality_vs_effect_scatter",
    modality="network_and_pathway",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Do the most-central nodes have the largest effect sizes?"
    ),
    required_fields=("node_names", "centrality", "effect_size"),
    optional_fields=("p_value", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("centrality_degree_distribution",),
)


@register_recipe(
    metadata=_META,
    contract=CentralityEffectInput,
    demo_contract=_demo,
)
def render(contract: CentralityEffectInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.6))
    AESTHETIC.apply_to_ax(ax)

    names = contract.node_names
    c = np.asarray(contract.centrality, float)
    e = np.asarray(contract.effect_size, float)
    p = (np.asarray(contract.p_value, float)
         if contract.p_value is not None else None)

    # Color by -log10(p).
    if p is not None:
        import matplotlib as mpl
        cmap = mpl.colormaps[AESTHETIC.continuous_cmap]
        neg_lp = -np.log10(np.clip(p, 1e-12, 1.0))
        sc = ax.scatter(c, e, s=18, c=neg_lp, cmap=cmap,
                        alpha=0.85, edgecolor="white", linewidth=0.3,
                        zorder=3)
        cbar = ax.figure.colorbar(sc, ax=ax, fraction=0.04, pad=0.03)
        cbar.set_label(r"$-\log_{10}(p)$", fontsize=6.8)
        cbar.ax.tick_params(labelsize=6.4)
    else:
        ax.scatter(c, e, s=18, color="#5E35B1", alpha=0.85,
                   edgecolor="white", linewidth=0.3, zorder=3)

    # OLS fit in log-x space.
    lx = np.log10(np.clip(c, 1e-6, None))
    slope, intercept = np.polyfit(lx, e, 1)
    xs = np.linspace(c.min(), c.max(), 100)
    ax.plot(xs, intercept + slope * np.log10(xs),
            color="#111111", lw=1.1, zorder=4,
            label=f"OLS: slope={smart_fmt(float(slope))}")

    r = float(np.corrcoef(lx, e)[0, 1]) if lx.std() > 0 else 0.0

    # Label top-right nodes (high centrality + high effect).
    top_score = np.log10(np.clip(c, 1, None)) + e
    top_idx = np.argsort(-top_score)[:5]
    for i in top_idx:
        ax.text(c[i], e[i], f"  {names[i]}",
                ha="left", va="center", fontsize=6.0, color="#111111",
                zorder=5)

    ax.set_xscale("log")
    ax.set_xlabel("centrality")
    ax.set_ylabel("effect size")
    ax.set_title(
        f"{contract.title}  ·  r = {smart_fmt(r)}, N = {int(c.size)}",
        fontsize=9.0, pad=4,
    )
    ax.legend(fontsize=6.6, frameon=False, loc="upper left",
              handlelength=1.4)
    ax.grid(which="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
