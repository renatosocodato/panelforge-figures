"""Pathway-flux Sankey-like — stacked flows between left (inputs) and right (outputs)."""

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


class SankeyFluxInput(RecipeContract):
    sources: list[str] = Field(...)
    targets: list[str] = Field(...)
    flow_matrix: list[list[float]] = Field(
        ..., description="flow[src][tgt] ≥ 0"
    )
    title: str = "Pathway flux"


def _demo() -> SankeyFluxInput:
    rng = np.random.default_rng(341)
    src = ["ROS input", "TLR ligand", "cytokine", "phagocytic load"]
    tgt = ["NFκB", "MAPK", "STAT1", "Nrf2", "Rho"]
    M = rng.uniform(0, 1, (len(src), len(tgt)))
    return SankeyFluxInput(
        sources=src, targets=tgt,
        flow_matrix=M.tolist(),
    )


_META = RecipeMetadata(
    name="pathway_flux_sankey_like",
    modality="network_and_pathway",
    family=RecipeFamily.matrix,
    answers_question="How do signaling inputs flow to downstream pathway nodes, with width ∝ contribution?",
    required_fields=("sources", "targets", "flow_matrix"),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("interaction_chord_diagram",),
)


@register_recipe(metadata=_META, contract=SankeyFluxInput, demo_contract=_demo)
def render(contract: SankeyFluxInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.6))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    M = np.array(contract.flow_matrix, dtype=float)
    n_src = len(contract.sources)
    n_tgt = len(contract.targets)
    src_totals = M.sum(axis=1)
    tgt_totals = M.sum(axis=0)
    total = max(M.sum(), 1e-9)

    # Vertical stack positions; heights proportional to totals.
    gap = 0.02
    src_y = np.cumsum(np.concatenate(([0], src_totals / total + gap)))
    tgt_y = np.cumsum(np.concatenate(([0], tgt_totals / total + gap)))

    ax.set_xlim(0, 1)
    ax.set_ylim(0, max(src_y[-1], tgt_y[-1]) + 0.05)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ("left", "bottom"):
        ax.spines[s].set_visible(False)

    # Source nodes (left bars).
    src_colors = [palette[i % len(palette.colors)] for i in range(n_src)]
    for i, name in enumerate(contract.sources):
        y_lo = src_y[i]
        h = src_totals[i] / total
        ax.fill_between([0.02, 0.08], y_lo, y_lo + h,
                        color=src_colors[i], alpha=0.9, zorder=4)
        ax.text(0.0, y_lo + h / 2, name, ha="right", va="center",
                fontsize=6.8, color="#222222")

    # Target nodes (right bars).
    tgt_colors = [palette[(n_src + i) % len(palette.colors)] for i in range(n_tgt)]
    for j, name in enumerate(contract.targets):
        y_lo = tgt_y[j]
        h = tgt_totals[j] / total
        ax.fill_between([0.92, 0.98], y_lo, y_lo + h,
                        color=tgt_colors[j], alpha=0.9, zorder=4)
        ax.text(1.0, y_lo + h / 2, name, ha="left", va="center",
                fontsize=6.8, color="#222222")

    # Flow ribbons — stack upwards within each src/tgt bar.
    src_progress = np.zeros(n_src)
    tgt_progress = np.zeros(n_tgt)
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MplPath

    for i in range(n_src):
        for j in range(n_tgt):
            flow = M[i, j] / total
            if flow <= 0:
                continue
            y_s_lo = src_y[i] + src_progress[i]
            y_s_hi = y_s_lo + flow
            y_t_lo = tgt_y[j] + tgt_progress[j]
            y_t_hi = y_t_lo + flow
            src_progress[i] += flow
            tgt_progress[j] += flow

            # Cubic Bezier ribbon.
            verts = [
                (0.08, y_s_lo),
                (0.5, y_s_lo), (0.5, y_t_lo),
                (0.92, y_t_lo),
                (0.92, y_t_hi),
                (0.5, y_t_hi), (0.5, y_s_hi),
                (0.08, y_s_hi),
                (0.08, y_s_lo),
            ]
            codes = [
                MplPath.MOVETO,
                MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
                MplPath.LINETO,
                MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
                MplPath.CLOSEPOLY,
            ]
            patch = PathPatch(MplPath(verts, codes),
                              facecolor=src_colors[i], alpha=0.35,
                              edgecolor="none", zorder=3)
            ax.add_patch(patch)

    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.figure.text(
        0.5, 0.005,
        f"total flow = {smart_fmt(float(total))}",
        ha="center", va="bottom",
        fontsize=6.2, color="#444444",
    )
    return ax
