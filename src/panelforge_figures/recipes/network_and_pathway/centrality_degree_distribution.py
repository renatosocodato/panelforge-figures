"""Centrality degree distribution — log-log rank-frequency with power-law fit."""

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


class CentralityInput(RecipeContract):
    degrees: list[int] = Field(..., description="per-node degree")
    node_names: list[str] | None = None
    title: str = "Degree distribution"


def _demo() -> CentralityInput:
    rng = np.random.default_rng(353)
    # Power-law-ish via Barabási-Albert-like sampling.
    n = 250
    alpha = 2.3
    degs = (rng.pareto(alpha - 1, n) + 1) * 2
    degs = np.clip(degs.astype(int), 1, None)
    names = [f"n{i:03d}" for i in range(n)]
    return CentralityInput(
        degrees=degs.tolist(),
        node_names=names,
    )


_META = RecipeMetadata(
    name="centrality_degree_distribution",
    modality="network_and_pathway",
    family=RecipeFamily.diagnostic_curve,
    answers_question="Is the network degree distribution heavy-tailed, and which nodes are the top hubs?",
    required_fields=("degrees",),
    optional_fields=("node_names", "title"),
    file_format_hints=("csv", "graphml"),
    alternatives_in_modality=("regulatory_network_hive",),
)


@register_recipe(metadata=_META, contract=CentralityInput, demo_contract=_demo)
def render(contract: CentralityInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    d = np.array(contract.degrees, dtype=float)
    d = d[d > 0]
    d_sorted = np.sort(d)[::-1]
    ranks = np.arange(1, d_sorted.size + 1)
    P = ranks / d_sorted.size

    ax.scatter(d_sorted, P, s=14, color=palette.pick("signaling"),
               alpha=0.7, edgecolor="white", linewidth=0.3, zorder=3,
               label="nodes")

    # Fit on top 30%.
    n_tail = max(10, int(0.30 * d_sorted.size))
    tail_d = d_sorted[:n_tail]
    tail_P = P[:n_tail]
    slope, intercept = np.polyfit(np.log(tail_d), np.log(tail_P), 1)
    alpha_est = -slope + 1
    fit_x = np.linspace(np.log(tail_d.min()), np.log(tail_d.max()), 60)
    ax.plot(np.exp(fit_x), np.exp(slope * fit_x + intercept),
            color="#D32F2F", lw=1.1, zorder=5,
            label=fr"power-law $\alpha$ = {smart_fmt(alpha_est)}")

    # Mean-degree reference.
    mean_d = float(d.mean())
    ax.axvline(mean_d, color="#888888", lw=0.6, ls="--", zorder=2)
    ax.text(mean_d, P.min() * 1.1,
            rf"$\langle k \rangle$={smart_fmt(mean_d)}",
            rotation=0, ha="left", va="bottom", fontsize=6.2, color="#555555",
            bbox=dict(boxstyle="round,pad=0.12", fc="white",
                      ec="none", alpha=0.9))

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("degree k")
    ax.set_ylabel(r"P($k' \geq k$)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="lower left",
              handlelength=1.8)

    # Top hubs callout.
    if contract.node_names is not None:
        order = np.argsort(-np.array(contract.degrees, dtype=int))[:3]
        hubs = "   ".join(
            f"{contract.node_names[i]} (k={contract.degrees[i]})"
            for i in order
        )
        ax.text(0.99, 0.97,
                f"top hubs: {hubs}",
                transform=ax.transAxes, ha="right", va="top",
                fontsize=6.2, color="#333333",
                bbox=dict(boxstyle="round,pad=0.18", fc="white",
                          ec="#BBBBBB", lw=0.5, alpha=0.92),
                zorder=6)
    ax.grid(axis="both", which="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
