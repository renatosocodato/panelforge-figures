"""Effect-size vs significance — scatter of |log2FC| vs -log10 padj."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    density_alpha,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class EffectSigInput(RecipeContract):
    log2fc: list[float] = Field(...)
    padj: list[float] = Field(...)
    gene_names: list[str] | None = None
    log2fc_threshold: float = 1.0
    padj_threshold: float = 0.05
    title: str = "Effect size vs significance"


def _demo() -> EffectSigInput:
    rng = np.random.default_rng(283)
    n = 1500
    fc = rng.normal(0, 0.7, n)
    p = rng.uniform(0.05, 1.0, n)
    hit = rng.choice(n, size=80, replace=False)
    fc[hit] = rng.choice([-1, 1], 80) * rng.uniform(1.3, 3.5, 80)
    p[hit] = rng.uniform(1e-8, 1e-3, 80)
    return EffectSigInput(
        log2fc=fc.tolist(),
        padj=p.tolist(),
        gene_names=[f"g{i:04d}" for i in range(n)],
    )


_META = RecipeMetadata(
    name="effect_size_vs_significance",
    modality="omics_differential",
    family=RecipeFamily.scatter_collapse,
    answers_question="How does effect size co-vary with statistical significance across genes?",
    required_fields=("log2fc", "padj"),
    optional_fields=("gene_names", "log2fc_threshold", "padj_threshold", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("volcano_labeled_repelled",),
)


@register_recipe(metadata=_META, contract=EffectSigInput, demo_contract=_demo)
def render(contract: EffectSigInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    fc = np.array(contract.log2fc, dtype=float)
    p = np.array(contract.padj, dtype=float)
    x = np.abs(fc)
    y = -np.log10(np.maximum(p, 1e-300))

    alpha = density_alpha(x, y)
    ax.scatter(x, y, s=10, color=palette[0], alpha=alpha,
               edgecolor="none", zorder=2)

    # Monotonic quantile "envelope" — max y per x bin.
    bins = np.linspace(0, x.max() * 1.05, 20)
    centers = 0.5 * (bins[:-1] + bins[1:])
    envelope = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (x >= lo) & (x < hi)
        envelope.append(np.nanquantile(y[mask], 0.9) if mask.any() else np.nan)
    ax.plot(centers, envelope, color="#111111", lw=1.0, zorder=5,
            label="90th percentile")

    # Thresholds.
    ax.axvline(contract.log2fc_threshold, color="#888888", lw=0.6, ls="--",
               zorder=1)
    ax.axhline(-np.log10(contract.padj_threshold),
               color="#888888", lw=0.6, ls="--", zorder=1)

    # Quadrant hit count.
    sig = (p < contract.padj_threshold) & (x > contract.log2fc_threshold)
    ax.text(0.99, 0.97,
            f"hits (upper-right): {int(sig.sum())}\n"
            f"N total = {len(fc)}",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=6.4, color="#333333",
            bbox=dict(boxstyle="round,pad=0.18", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=7)

    ax.set_xlabel(r"$|\log_2$FC$|$")
    ax.set_ylabel(r"$-\log_{10}$ p$_{adj}$")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="upper left",
              handlelength=1.6)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    _ = smart_fmt
    return ax
