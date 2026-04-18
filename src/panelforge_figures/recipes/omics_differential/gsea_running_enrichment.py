"""GSEA running enrichment score — ES trace + hit rug + leading-edge shading."""

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


class GSEAInput(RecipeContract):
    ranked_scores: list[float] = Field(...)
    hit_ranks: list[int] = Field(..., description="indices where pathway members hit")
    pathway: str = "Pathway"
    nes: float = 0.0
    fdr: float = 1.0
    title: str = "GSEA running enrichment"


def _demo() -> GSEAInput:
    rng = np.random.default_rng(269)
    n = 1200
    # Ranked scores decreasing from top to bottom.
    ranks_desc = np.linspace(3, -3, n) + rng.normal(0, 0.1, n)
    # Pathway members concentrated in top ~10%.
    hits = np.sort(rng.choice(n, size=55, replace=False))
    # Bias top half.
    top_hits = rng.choice(int(n * 0.18), size=30, replace=False)
    hits = np.unique(np.concatenate([hits, top_hits]))
    return GSEAInput(
        ranked_scores=ranks_desc.tolist(),
        hit_ranks=hits.tolist(),
        pathway="Inflammatory response",
        nes=2.38,
        fdr=0.0012,
    )


def _running_es(n: int, hits: np.ndarray) -> np.ndarray:
    """Simplified enrichment score random walk."""
    is_hit = np.zeros(n, dtype=bool)
    is_hit[hits] = True
    hit_boost = 1.0 / max(is_hit.sum(), 1)
    miss_penalty = 1.0 / max(n - is_hit.sum(), 1)
    steps = np.where(is_hit, hit_boost, -miss_penalty)
    return np.cumsum(steps)


_META = RecipeMetadata(
    name="gsea_running_enrichment",
    modality="omics_differential",
    family=RecipeFamily.diagnostic_curve,
    answers_question="Where in the ranked gene list do members of a gene set concentrate, and what is the resulting enrichment score?",
    required_fields=("ranked_scores", "hit_ranks"),
    optional_fields=("pathway", "nes", "fdr", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("ora_dotplot_by_ontology",),
)


@register_recipe(metadata=_META, contract=GSEAInput, demo_contract=_demo)
def render(contract: GSEAInput, ax=None, **_):
    """Split axis into 3 rows: ES curve, hit rug, ranked-score bar."""
    import matplotlib.pyplot as plt
    if ax is None:
        fig = plt.figure(figsize=(5.4, 3.6))
        gs = fig.add_gridspec(3, 1, height_ratios=[4, 0.5, 1.2],
                              hspace=0.12)
        ax_es = fig.add_subplot(gs[0])
        ax_rug = fig.add_subplot(gs[1], sharex=ax_es)
        ax_bar = fig.add_subplot(gs[2], sharex=ax_es)
    else:
        fig = ax.figure
        pos = ax.get_subplotspec()
        ax.remove()
        sub = pos.subgridspec(3, 1, height_ratios=[4, 0.5, 1.2], hspace=0.12)
        ax_es = fig.add_subplot(sub[0])
        ax_rug = fig.add_subplot(sub[1], sharex=ax_es)
        ax_bar = fig.add_subplot(sub[2], sharex=ax_es)

    for a in (ax_es, ax_rug, ax_bar):
        AESTHETIC.apply_to_ax(a)
    palette = get_palette(AESTHETIC.primary_palette)

    scores = np.array(contract.ranked_scores, dtype=float)
    hits = np.array(contract.hit_ranks, dtype=int)
    n = scores.size
    x = np.arange(n)
    es = _running_es(n, hits)
    i_peak = int(np.argmax(np.abs(es)))
    es_peak = es[i_peak]

    # Leading-edge shading: 0 → peak.
    lead_color = palette[1]
    ax_es.fill_between(x[: i_peak + 1], 0, es[: i_peak + 1],
                       color=lead_color, alpha=0.22, linewidth=0, zorder=2,
                       label="leading edge")
    ax_es.plot(x, es, color="#111111", lw=1.1, zorder=4, label="ES")
    ax_es.axhline(0, color="#888888", lw=0.4, ls=":", zorder=1)
    ax_es.legend(fontsize=6.4, frameon=False, loc="upper right",
                 handlelength=1.4)
    ax_es.scatter([i_peak], [es_peak], s=40, marker="*", color="#D32F2F",
                  edgecolor="white", linewidth=0.7, zorder=5)
    ax_es.set_ylabel("ES")
    ax_es.set_title(contract.title, fontsize=9.0, pad=4)
    ax_es.tick_params(labelbottom=False)
    ax_es.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax_es.set_axisbelow(True)

    # Hit rug.
    for h in hits:
        ax_rug.axvline(h, color="#111111", lw=0.35, alpha=0.85, zorder=3)
    ax_rug.set_yticks([])
    ax_rug.set_ylim(0, 1)
    ax_rug.tick_params(labelbottom=False)
    for s in ("left",):
        ax_rug.spines[s].set_visible(False)

    # Ranked-score horizontal bar.
    cmap = "RdBu_r"
    ax_bar.imshow(scores[np.newaxis, :],
                  cmap=cmap, aspect="auto",
                  extent=(0, n, 0, 1),
                  vmin=-abs(scores).max(), vmax=abs(scores).max(),
                  interpolation="nearest")
    ax_bar.set_yticks([])
    ax_bar.set_xlabel("rank in ordered gene list")

    # Pathway + stats callout.
    ax_es.text(0.01, 0.99,
               f"{contract.pathway}\n"
               f"NES = {smart_fmt(contract.nes)}   "
               f"FDR = {smart_fmt(contract.fdr)}   "
               f"leading edge n = {i_peak + 1}",
               transform=ax_es.transAxes, ha="left", va="top",
               fontsize=6.6, color="#333333",
               bbox=dict(boxstyle="round,pad=0.20", fc="white",
                         ec="#BBBBBB", lw=0.5, alpha=0.92),
               zorder=6)
    return ax_es
