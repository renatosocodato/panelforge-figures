"""Raw vs shrunken log2FC scatter — where does empirical-Bayes shrinkage matter?

Each gene's raw MLE log2FC is on x; the shrunken (e.g., apeglm /
ashr / adaptive-shrinkage) estimate on y. The identity line is the
reference; genes below / above it are shrunken toward / away from
zero. A shrinkage-ratio color coding and a "|Δ| > threshold" callout
highlight the genes most affected.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    empty_data_guard,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class ShrinkageScatterInput(RecipeContract):
    gene_names: list[str] = Field(...)
    raw_log2fc: list[float] = Field(...)
    shrunken_log2fc: list[float] = Field(...)
    shrinkage_method: str = "apeglm"
    shrinkage_threshold: float = Field(
        default=0.6,
        description="|raw - shrunken| above this counts as 'strongly shrunken'",
    )
    title: str = "Raw vs shrunken effect size"


def _demo() -> ShrinkageScatterInput:
    rng = np.random.default_rng(613)
    n = 1200
    names = [f"g{i:05d}" for i in range(n)]
    raw = rng.normal(0, 1.4, n)
    # Shrinkage factor depends on |raw|: low-abundance genes shrink more.
    amp = np.abs(raw)
    shrink = amp / (amp + 0.8)        # ∈ (0, 1)
    shrunken = raw * shrink
    return ShrinkageScatterInput(
        gene_names=names,
        raw_log2fc=raw.tolist(),
        shrunken_log2fc=shrunken.tolist(),
        shrinkage_method="apeglm",
    )


_META = RecipeMetadata(
    name="shrinkage_estimate_scatter",
    modality="omics_differential",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "How does an empirical-Bayes-shrunken effect estimate compare "
        "to the raw MLE estimate, and where does shrinkage matter most?"
    ),
    required_fields=("gene_names", "raw_log2fc", "shrunken_log2fc"),
    optional_fields=(
        "shrinkage_method", "shrinkage_threshold", "title",
    ),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=(
        "effect_size_vs_significance", "volcano_labeled_repelled",
    ),
)


@register_recipe(
    metadata=_META,
    contract=ShrinkageScatterInput,
    demo_contract=_demo,
)
def render(contract: ShrinkageScatterInput, ax=None, **_):
    import matplotlib as mpl

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.6, 4.0))
    AESTHETIC.apply_to_ax(ax)
    if empty_data_guard(ax, len(contract.raw_log2fc), message="no genes"):
        return ax

    raw = np.asarray(contract.raw_log2fc, float)
    shr = np.asarray(contract.shrunken_log2fc, float)
    mask = np.isfinite(raw) & np.isfinite(shr)
    raw = raw[mask]
    shr = shr[mask]

    shrink_ratio = np.where(np.abs(raw) > 1e-6, 1 - np.abs(shr) / np.abs(raw), 0.0)
    shrink_ratio = np.clip(shrink_ratio, 0, 1)

    cmap = mpl.colormaps["magma"]
    sc = ax.scatter(raw, shr, c=shrink_ratio, cmap=cmap, s=10,
                    vmin=0.0, vmax=1.0, alpha=0.85,
                    edgecolor="none", zorder=3, label="genes")

    # Identity line.
    lo = float(min(raw.min(), shr.min()))
    hi = float(max(raw.max(), shr.max()))
    span = hi - lo
    ax.plot([lo - 0.05 * span, hi + 0.05 * span],
            [lo - 0.05 * span, hi + 0.05 * span],
            color="#111111", lw=0.8, ls="--", zorder=4,
            label="y = x (no shrinkage)")

    # Strong-shrinkage threshold markers (|Δ| > threshold) — smaller and
    # thinner outline so the magma shrinkage-ratio colormap remains
    # readable under the highlight.
    delta = raw - shr
    strong = np.abs(delta) > contract.shrinkage_threshold
    if strong.any():
        ax.scatter(raw[strong], shr[strong], s=14, facecolor="none",
                   edgecolor="#D32F2F", linewidth=0.5, zorder=5,
                   label=f"|Δ|>{smart_fmt(contract.shrinkage_threshold)} ({int(strong.sum())})")

    cbar = ax.figure.colorbar(sc, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("shrinkage ratio", fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    ax.set_xlabel(r"raw $\log_2$FC (MLE)")
    ax.set_ylabel(r"shrunken $\log_2$FC")
    ax.set_xlim(lo - 0.05 * span, hi + 0.05 * span)
    ax.set_ylim(lo - 0.05 * span, hi + 0.05 * span)
    ax.set_aspect("equal")
    ax.set_title(
        f"{contract.title}  ·  method: {contract.shrinkage_method}",
        fontsize=9.0, pad=4,
    )
    ax.legend(fontsize=6.4, frameon=False, loc="upper left",
              handlelength=1.4)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    ax.text(
        0.98, 0.03,
        f"median shrinkage = {smart_fmt(float(np.median(shrink_ratio)))}\n"
        f"strongly shrunken: {int(strong.sum())}",
        transform=ax.transAxes, ha="right", va="bottom",
        fontsize=6.4, color="#333333",
        bbox=dict(boxstyle="round,pad=0.22", fc="white",
                  ec="#BBBBBB", lw=0.5, alpha=0.92),
        zorder=6,
    )
    return ax
