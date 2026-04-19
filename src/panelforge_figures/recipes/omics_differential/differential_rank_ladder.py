"""Differential rank ladder — top-N up and down genes ranked with effect size."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    empty_data_guard,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class DiffRankLadderInput(RecipeContract):
    gene_names: list[str] = Field(...)
    log2fc: list[float] = Field(...)
    padj: list[float] = Field(...)
    top_n_per_direction: int = 15
    title: str = "Top-up / top-down genes"


def _demo() -> DiffRankLadderInput:
    rng = np.random.default_rng(277)
    n = 40
    genes = [f"GENE{i:02d}" for i in range(n)]
    # Mix of up and down.
    fc = np.concatenate([
        rng.uniform(1.5, 5.0, n // 2),
        -rng.uniform(1.0, 4.0, n // 2),
    ])
    rng.shuffle(fc)
    p = 10 ** -rng.uniform(2, 16, n)
    return DiffRankLadderInput(
        gene_names=genes,
        log2fc=fc.tolist(),
        padj=p.tolist(),
        top_n_per_direction=10,
    )


_META = RecipeMetadata(
    name="differential_rank_ladder",
    modality="omics_differential",
    family=RecipeFamily.ladder,
    answers_question="What are the top-N most up- and down-regulated genes, ranked with effect-size bars?",
    required_fields=("gene_names", "log2fc", "padj"),
    optional_fields=("top_n_per_direction", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("volcano_labeled_repelled",),
)


@register_recipe(metadata=_META, contract=DiffRankLadderInput, demo_contract=_demo)
def render(contract: DiffRankLadderInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.8))
    AESTHETIC.apply_to_ax(ax)
    if empty_data_guard(ax, len(contract.log2fc), message="no genes"):
        return ax
    palette = get_palette(AESTHETIC.primary_palette)

    fc = np.array(contract.log2fc, dtype=float)
    p = np.array(contract.padj, dtype=float)

    # Top-N by fc sign and magnitude.
    k = contract.top_n_per_direction
    up_idx = np.argsort(-fc)[:k]
    dn_idx = np.argsort(fc)[:k]

    # Plot order: down at bottom, up at top, dividing line in middle.
    y_up = np.arange(k)[::-1] + k + 1.5
    y_dn = np.arange(k)[::-1]

    ax.barh(y_up, fc[up_idx], color=palette[1], alpha=0.85,
            edgecolor="white", linewidth=0.5, zorder=3,
            label=f"top {k} up")
    ax.barh(y_dn, fc[dn_idx], color=palette[0], alpha=0.85,
            edgecolor="white", linewidth=0.5, zorder=3,
            label=f"top {k} down")

    # Zero reference.
    ax.axvline(0, color="#555555", lw=0.6, zorder=1)

    # Right-of-bar numeric labels.
    xmax = max(float(fc[up_idx].max()), 0.5)
    xmin = min(float(fc[dn_idx].min()), -0.5)
    span = xmax - xmin
    ax.set_xlim(xmin - 0.40 * span, xmax + 0.40 * span)

    for yi, i in zip(y_up, up_idx):
        ax.text(fc[i] + 0.015 * span, yi,
                f"{smart_fmt(fc[i])}  p={smart_fmt(p[i])}",
                va="center", ha="left", fontsize=5.8, color="#222222")
    for yi, i in zip(y_dn, dn_idx):
        ax.text(fc[i] - 0.015 * span, yi,
                f"{smart_fmt(fc[i])}  p={smart_fmt(p[i])}",
                va="center", ha="right", fontsize=5.8, color="#222222")

    ax.set_yticks(list(y_up) + list(y_dn))
    ax.set_yticklabels(
        [contract.gene_names[i] for i in list(up_idx) + list(dn_idx)],
        fontsize=6.8,
    )
    ax.set_xlabel(r"$\log_2$ fold-change")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="lower right",
              handlelength=1.4)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
