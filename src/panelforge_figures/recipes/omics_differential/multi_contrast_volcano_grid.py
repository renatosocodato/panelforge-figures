"""Multi-contrast volcano grid — 2×2 or 1×N mini-volcanos across contrasts."""

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


class MultiVolcanoInput(RecipeContract):
    contrasts: dict[str, dict[str, list[float]]] = Field(
        ..., description="contrast → {'log2fc': [...], 'padj': [...]}"
    )
    log2fc_threshold: float = 1.0
    padj_threshold: float = 0.05
    title: str = "Contrast grid · volcanos"


def _demo() -> MultiVolcanoInput:
    contrasts: dict[str, dict[str, list[float]]] = {}
    for name, seed, n_hits in [
        ("WT vs KO", 1, 70),
        ("F vs M", 2, 30),
        ("LPS vs vehicle", 3, 140),
        ("LPS × sex", 4, 15),
    ]:
        local = np.random.default_rng(seed)
        n = 1500
        fc = local.normal(0, 0.5, n)
        p = local.uniform(0.1, 1.0, n)
        hits = local.choice(n, size=n_hits, replace=False)
        fc[hits] = local.choice([-1, 1], n_hits) * local.uniform(1.2, 3.5, n_hits)
        p[hits] = local.uniform(1e-8, 1e-3, n_hits)
        contrasts[name] = {"log2fc": fc.tolist(), "padj": p.tolist()}
    return MultiVolcanoInput(contrasts=contrasts)


_META = RecipeMetadata(
    name="multi_contrast_volcano_grid",
    modality="omics_differential",
    family=RecipeFamily.volcano,
    answers_question="How do differential-expression landscapes compare across multiple contrasts at a glance?",
    required_fields=("contrasts",),
    optional_fields=("log2fc_threshold", "padj_threshold", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("volcano_labeled_repelled", "upset_set_comparisons"),
)


@register_recipe(metadata=_META, contract=MultiVolcanoInput, demo_contract=_demo)
def render(contract: MultiVolcanoInput, ax=None, **_):
    """Split host axis into a grid of mini-volcanos."""
    import matplotlib.pyplot as plt
    n_panels = len(contract.contrasts)
    ncols = 2 if n_panels >= 3 else n_panels
    nrows = (n_panels + ncols - 1) // ncols

    if ax is None:
        fig = plt.figure(figsize=(5.4, 3.4))
        gs = fig.add_gridspec(nrows, ncols, hspace=0.35, wspace=0.28)
        axes = [fig.add_subplot(gs[r, c])
                for r in range(nrows) for c in range(ncols)
                if r * ncols + c < n_panels]
    else:
        fig = ax.figure
        pos = ax.get_subplotspec()
        ax.remove()
        sub = pos.subgridspec(nrows, ncols, hspace=0.35, wspace=0.28)
        axes = [fig.add_subplot(sub[r, c])
                for r in range(nrows) for c in range(ncols)
                if r * ncols + c < n_panels]
    for a in axes:
        AESTHETIC.apply_to_ax(a)

    palette = get_palette(AESTHETIC.primary_palette)

    names = list(contract.contrasts.keys())
    for ai, name in zip(axes, names):
        data = contract.contrasts[name]
        fc = np.array(data["log2fc"], dtype=float)
        p = np.array(data["padj"], dtype=float)
        y = -np.log10(np.maximum(p, 1e-300))
        sig = (p < contract.padj_threshold) & (np.abs(fc) > contract.log2fc_threshold)
        ns = ~sig
        up = sig & (fc > 0)
        dn = sig & (fc < 0)

        alpha_ns = density_alpha(fc[ns], y[ns]) if ns.any() else np.array([])
        ai.scatter(fc[ns], y[ns], s=5, c="#BBBBBB", alpha=alpha_ns,
                   edgecolor="none", zorder=2)
        ai.scatter(fc[up], y[up], s=9, c=palette[1], alpha=0.9,
                   edgecolor="none", zorder=3)
        ai.scatter(fc[dn], y[dn], s=9, c=palette[0], alpha=0.9,
                   edgecolor="none", zorder=3)
        ai.axhline(-np.log10(contract.padj_threshold),
                   color="#888888", lw=0.4, ls="--", zorder=1)
        ai.axvline(contract.log2fc_threshold, color="#888888",
                   lw=0.4, ls="--", zorder=1)
        ai.axvline(-contract.log2fc_threshold, color="#888888",
                   lw=0.4, ls="--", zorder=1)
        ai.set_title(
            f"{name}  ((up){int(up.sum())} (down){int(dn.sum())})",
            fontsize=7.0, pad=2,
        )
        ai.set_xlabel(r"$\log_2$FC", fontsize=6.4)
        ai.set_ylabel(r"$-\log_{10}$p", fontsize=6.4)
        ai.tick_params(labelsize=5.6)
        ai.grid(axis="both", color="#EEEEEE", lw=0.3, zorder=0)
        ai.set_axisbelow(True)

    fig.suptitle(contract.title, fontsize=9.4, y=1.01)
    _ = smart_fmt
    return axes[0]
