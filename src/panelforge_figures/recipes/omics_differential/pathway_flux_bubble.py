"""Pathway-flux bubble — per-pathway activity score × direction with size ∝ members."""

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


class PathwayBubbleInput(RecipeContract):
    pathways: list[str] = Field(...)
    activity_score: list[float] = Field(..., description="signed activity score (direction)")
    n_members: list[int] = Field(..., description="genes in pathway hit")
    significance: list[float] = Field(..., description="-log10 padj")
    title: str = "Pathway flux"


def _demo() -> PathwayBubbleInput:
    rng = np.random.default_rng(281)
    paths = [
        "Inflammation (up)",
        "Phagocytosis (up)",
        "Metabolism (down)",
        "Autophagy (up)",
        "TGF-β (down)",
        "OXPHOS (down)",
        "Migration (up)",
        "Cytokine secretion (up)",
        "Proliferation (down)",
        "Neurotrophic (up)",
    ]
    act = np.array([2.1, 1.7, -1.8, 1.3, -1.1, -2.5, 1.4, 2.3, -1.0, 0.9])
    n = rng.integers(8, 80, len(paths))
    sig = rng.uniform(2, 14, len(paths))
    return PathwayBubbleInput(
        pathways=paths,
        activity_score=act.tolist(),
        n_members=n.tolist(),
        significance=sig.tolist(),
    )


_META = RecipeMetadata(
    name="pathway_flux_bubble",
    modality="omics_differential",
    family=RecipeFamily.matrix,
    answers_question="Which pathways are activated or suppressed, scaled by member count and significance?",
    required_fields=("pathways", "activity_score", "n_members", "significance"),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("ora_dotplot_by_ontology",),
)


@register_recipe(metadata=_META, contract=PathwayBubbleInput, demo_contract=_demo)
def render(contract: PathwayBubbleInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.6))
    AESTHETIC.apply_to_ax(ax)

    act = np.array(contract.activity_score, dtype=float)
    n = np.array(contract.n_members, dtype=float)
    sig = np.array(contract.significance, dtype=float)
    order = np.argsort(-np.abs(act))

    y = np.arange(len(contract.pathways))[::-1]
    paths = [contract.pathways[i] for i in order]
    act = act[order]
    n = n[order]
    sig = sig[order]

    # Bubbles colored by activity (RdBu_r), sized by n_members.
    vmax = max(abs(act.min()), abs(act.max()))
    sc = ax.scatter(act, y, s=n * 8, c=act,
                    cmap=AESTHETIC.ratio_cmap or "RdBu_r",
                    vmin=-vmax, vmax=vmax,
                    alpha=0.9, edgecolor="white", linewidth=0.5,
                    zorder=3)

    # Zero reference.
    ax.axvline(0, color="#555555", lw=0.6, ls="--", zorder=1)

    # Per-row significance on the right margin.
    for yi, s in zip(y, sig):
        ax.text(ax.get_xlim()[1] if False else vmax * 1.15, yi,
                f"$-\\log_{{10}}$p={smart_fmt(s)}",
                va="center", ha="left", fontsize=6.0, color="#333333")

    ax.set_yticks(y)
    ax.set_yticklabels(paths, fontsize=6.8)
    ax.set_xlabel("activity score")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.set_xlim(-vmax * 1.2, vmax * 1.55)

    cbar = ax.figure.colorbar(sc, ax=ax, fraction=0.035, pad=0.04)
    cbar.set_label("activity", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)

    # Size legend.
    from matplotlib.lines import Line2D
    size_vals = [int(n.min()), int(np.median(n)), int(n.max())]
    proxies = [
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor="#888888", markeredgecolor="white",
               markersize=np.sqrt(v * 8), label=f"n={v}")
        for v in size_vals
    ]
    ax.legend(handles=proxies, loc="lower right",
              fontsize=6.2, frameon=False, handlelength=1.0,
              title="genes", title_fontsize=6.4)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
