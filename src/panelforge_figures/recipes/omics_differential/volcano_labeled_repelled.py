"""Volcano plot — log2FC vs -log10 padj with top-N repelled labels + density alpha."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    density_alpha,
    empty_data_guard,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class VolcanoInput(RecipeContract):
    gene_names: list[str] = Field(...)
    log2fc: list[float] = Field(...)
    padj: list[float] = Field(...)
    log2fc_threshold: float = 1.0
    padj_threshold: float = 0.05
    top_n_labels: int = 6
    title: str = "Volcano plot"


def _demo() -> VolcanoInput:
    rng = np.random.default_rng(251)
    n = 2500
    genes = [f"g{i:05d}" for i in range(n)]
    # Bulk near 0 FC, non-significant; ~5% hits left and right.
    fc = rng.normal(0, 0.6, n)
    p = rng.uniform(0.1, 1.0, n)
    hit_idx = rng.choice(n, size=80, replace=False)
    fc[hit_idx] = rng.choice([-1, 1], 80) * rng.uniform(1.2, 4.0, 80)
    p[hit_idx] = rng.uniform(1e-8, 1e-3, 80)
    return VolcanoInput(
        gene_names=genes,
        log2fc=fc.tolist(),
        padj=p.tolist(),
        top_n_labels=6,
    )


def _repel_labels(xs, ys, texts, ax, fontsize=6.4, y_step=0.5, x_pad=0.15):
    """Very simple label-repulsion: push overlapping labels vertically."""
    order = np.argsort(-np.asarray(ys))       # largest -log10p first
    placed = []
    artists = []
    for i in order:
        x = xs[i]
        y = ys[i]
        # Bump up if too close to a placed label in x.
        while any(abs(x - px) < x_pad and abs(y - py) < y_step
                  for (px, py) in placed):
            y += y_step
        placed.append((x, y))
        t = ax.text(x, y, texts[i], fontsize=fontsize, color="#111111",
                    ha="left" if x >= 0 else "right", va="bottom",
                    bbox=dict(boxstyle="round,pad=0.12", fc="white",
                              ec="none", alpha=0.85), zorder=6)
        # Line from marker to label.
        ax.plot([xs[i], x], [ys[i], y], color="#888888", lw=0.4, zorder=5)
        artists.append(t)
    return artists


_META = RecipeMetadata(
    name="volcano_labeled_repelled",
    modality="omics_differential",
    family=RecipeFamily.volcano,
    answers_question="Which genes show significant differential expression, and which are the most notable hits by effect size and significance?",
    required_fields=("gene_names", "log2fc", "padj"),
    optional_fields=("log2fc_threshold", "padj_threshold", "top_n_labels", "title"),
    file_format_hints=("csv", "parquet", "tsv"),
    alternatives_in_modality=("ma_plot_with_lowess", "multi_contrast_volcano_grid"),
    n_points_typical=">1000 genes",
)


@register_recipe(metadata=_META, contract=VolcanoInput, demo_contract=_demo)
def render(contract: VolcanoInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.6))
    AESTHETIC.apply_to_ax(ax)
    if empty_data_guard(ax, len(contract.log2fc), message="no genes"):
        return ax
    palette = get_palette(AESTHETIC.primary_palette)

    fc = np.array(contract.log2fc, dtype=float)
    p = np.array(contract.padj, dtype=float)
    y = -np.log10(np.maximum(p, 1e-300))
    genes = contract.gene_names

    # Significance mask.
    sig = (p < contract.padj_threshold) & (np.abs(fc) > contract.log2fc_threshold)
    up = sig & (fc > 0)
    down = sig & (fc < 0)
    ns = ~sig

    # Alpha by local density (cheap, reduces over-plotting).
    alpha_ns = density_alpha(fc[ns], y[ns]) if ns.any() else np.array([])
    ax.scatter(fc[ns], y[ns], s=8, c="#BBBBBB", alpha=alpha_ns,
               edgecolor="none", zorder=2, label=f"n.s. ({ns.sum()})")
    ax.scatter(fc[up], y[up], s=16, c=palette[1], alpha=0.85,
               edgecolor="white", linewidth=0.3, zorder=3,
               label=f"up ({up.sum()})")
    ax.scatter(fc[down], y[down], s=16, c=palette[0], alpha=0.85,
               edgecolor="white", linewidth=0.3, zorder=3,
               label=f"down ({down.sum()})")

    # Thresholds.
    ax.axvline(contract.log2fc_threshold, color="#888888",
               lw=0.6, ls="--", zorder=1)
    ax.axvline(-contract.log2fc_threshold, color="#888888",
               lw=0.6, ls="--", zorder=1)
    ax.axhline(-np.log10(contract.padj_threshold), color="#888888",
               lw=0.6, ls="--", zorder=1)

    # Top-N labels by combined rank (|fc| and -log10 p both large).
    score = np.abs(fc) * y
    top_idx = np.argsort(-score)[: contract.top_n_labels]
    _repel_labels(
        fc[top_idx], y[top_idx], [genes[i] for i in top_idx],
        ax, fontsize=6.4,
        y_step=0.10 * (y.max() - y.min()),
        x_pad=0.18 * (fc.max() - fc.min()),
    )

    ax.set_xlabel(r"$\log_2$ fold-change")
    ax.set_ylabel(r"$-\log_{10}$ p$_{adj}$")
    ax.set_title(
        f"{contract.title}  ·  N={len(fc)},  "
        f"|log2FC|>{smart_fmt(contract.log2fc_threshold)},  "
        f"p$_{{adj}}$<{smart_fmt(contract.padj_threshold)}",
        fontsize=8.4, pad=4,
    )
    ax.legend(fontsize=6.6, frameon=True, facecolor="white",
              edgecolor="#CCCCCC", framealpha=0.92,
              loc="upper center", bbox_to_anchor=(0.5, 0.99),
              ncol=3, handlelength=1.2, handletextpad=0.4,
              columnspacing=1.6)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
