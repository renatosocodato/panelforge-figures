"""ORA dotplot — pathway enrichment with size ∝ gene count, color ∝ padj."""

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


class ORADotplotInput(RecipeContract):
    pathways: list[str] = Field(..., min_length=3)
    ontologies: list[str] = Field(..., description="one per pathway (e.g. BP/MF/CC)")
    gene_ratio: list[float] = Field(..., description="fraction of pathway genes in hit list")
    gene_count: list[int] = Field(...)
    padj: list[float] = Field(...)
    title: str = "Over-representation analysis"


def _demo() -> ORADotplotInput:
    paths = [
        "Cytokine signaling",
        "Rho GTPase cycle",
        "Actin cytoskeleton",
        "Innate immune response",
        "Oxidative phosphorylation",
        "TGF-β signaling",
        "TLR4 cascade",
        "MHC class II presentation",
        "Complement and coagulation",
        "Phagocytosis",
    ]
    onts = ["BP", "BP", "CC", "BP", "BP", "BP", "BP", "BP", "BP", "BP"]
    gr = [0.18, 0.14, 0.09, 0.11, 0.05, 0.09, 0.12, 0.07, 0.10, 0.13]
    gc = [42, 34, 22, 27, 11, 21, 29, 16, 24, 31]
    padj = [1e-18, 1e-14, 1e-5, 1e-12, 1e-3, 1e-6, 1e-11, 1e-4, 1e-7, 1e-10]
    return ORADotplotInput(
        pathways=paths, ontologies=onts,
        gene_ratio=gr, gene_count=gc, padj=padj,
    )


_META = RecipeMetadata(
    name="ora_dotplot_by_ontology",
    modality="omics_differential",
    family=RecipeFamily.matrix,
    answers_question="Which pathways are over-represented in the hit list, and how do they rank by gene ratio and padj?",
    required_fields=("pathways", "ontologies", "gene_ratio", "gene_count", "padj"),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("gsea_running_enrichment",),
)


@register_recipe(metadata=_META, contract=ORADotplotInput, demo_contract=_demo)
def render(contract: ORADotplotInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.6))
    AESTHETIC.apply_to_ax(ax)

    gr = np.array(contract.gene_ratio, dtype=float)
    gc = np.array(contract.gene_count, dtype=float)
    padj = np.array(contract.padj, dtype=float)
    nlp = -np.log10(np.maximum(padj, 1e-300))

    # Sort by ascending padj for top-to-bottom-priority layout.
    order = np.argsort(padj)
    gr = gr[order]
    gc = gc[order]
    nlp = nlp[order]
    paths = [contract.pathways[i] for i in order]
    onts = [contract.ontologies[i] for i in order]

    y = np.arange(len(paths))[::-1]
    sc = ax.scatter(gr, y, s=gc * 6, c=nlp,
                    cmap="viridis", alpha=0.9,
                    edgecolor="white", linewidth=0.5)

    # Per-row ontology tag (left of path label).
    ax.set_yticks(y)
    ax.set_yticklabels([f"{o}  ·  {p}" for o, p in zip(onts, paths)],
                       fontsize=6.6)
    ax.set_xlabel("gene ratio")
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    cbar = ax.figure.colorbar(sc, ax=ax, fraction=0.035, pad=0.04)
    cbar.set_label(r"$-\log_{10}$ p$_{adj}$", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)

    # Size legend (via proxies).
    from matplotlib.lines import Line2D
    size_legend_values = [int(gc.min()), int(np.median(gc)), int(gc.max())]
    proxies = [
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor="#888888", markeredgecolor="white",
               markersize=np.sqrt(v * 6), label=f"n={v}")
        for v in size_legend_values
    ]
    ax.legend(handles=proxies, loc="lower right",
              fontsize=6.4, frameon=False, handlelength=1.0,
              title="gene count", title_fontsize=6.6)

    ax.text(0.01, -0.16,
            f"N pathways = {len(paths)}   "
            f"min FDR = {smart_fmt(float(padj.min()))}",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.4, color="#333333",
            bbox=dict(boxstyle="round,pad=0.18", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=5)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
