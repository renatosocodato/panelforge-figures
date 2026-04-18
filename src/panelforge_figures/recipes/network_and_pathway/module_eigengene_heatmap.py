"""Module eigengene heatmap — WGCNA-style module × sample expression summary."""

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


class ModuleEigengeneInput(RecipeContract):
    module_names: list[str] = Field(...)
    sample_names: list[str] = Field(...)
    eigengene_matrix: list[list[float]] = Field(
        ..., description="module × sample eigengene values (z-scored)"
    )
    sample_conditions: list[str] = Field(default_factory=list)
    title: str = "Module eigengene"


def _demo() -> ModuleEigengeneInput:
    rng = np.random.default_rng(347)
    modules = [f"ME{c}" for c in ("brown", "blue", "turquoise",
                                    "yellow", "green", "grey")]
    conditions = ["ctrl"] * 6 + ["LPS 1h"] * 6 + ["LPS 6h"] * 6
    samples = [f"s{i:02d}" for i in range(len(conditions))]
    # Fake structure: turquoise up in LPS.
    M = rng.normal(0, 0.5, (len(modules), len(conditions)))
    for si, c in enumerate(conditions):
        if c == "LPS 1h":
            M[2, si] += 1.5
            M[1, si] -= 0.8
        if c == "LPS 6h":
            M[2, si] += 0.9
            M[0, si] += 1.0
    return ModuleEigengeneInput(
        module_names=modules,
        sample_names=samples,
        eigengene_matrix=M.tolist(),
        sample_conditions=conditions,
    )


_META = RecipeMetadata(
    name="module_eigengene_heatmap",
    modality="network_and_pathway",
    family=RecipeFamily.heatmap,
    answers_question="How does each co-expression module's eigengene vary across samples and conditions?",
    required_fields=("module_names", "sample_names", "eigengene_matrix"),
    optional_fields=("sample_conditions", "title"),
    file_format_hints=("csv", "parquet", "rds"),
    alternatives_in_modality=("centrality_degree_distribution",),
)


@register_recipe(metadata=_META, contract=ModuleEigengeneInput, demo_contract=_demo)
def render(contract: ModuleEigengeneInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.4))
    AESTHETIC.apply_to_ax(ax)

    M = np.array(contract.eigengene_matrix, dtype=float)
    vmax = max(abs(M.min()), abs(M.max()))
    im = ax.imshow(
        M, cmap=AESTHETIC.ratio_cmap or "RdBu_r",
        vmin=-vmax, vmax=vmax, aspect="auto",
        interpolation="nearest",
    )
    ax.set_xticks(range(len(contract.sample_names)))
    ax.set_xticklabels(contract.sample_names, rotation=60, ha="right",
                       fontsize=5.6)
    ax.set_yticks(range(len(contract.module_names)))
    ax.set_yticklabels(contract.module_names, fontsize=6.6)
    ax.set_title(contract.title, fontsize=9.0, pad=14)

    # Condition strip above x-axis if available.
    if contract.sample_conditions:
        from matplotlib.patches import Patch
        unique = list(dict.fromkeys(contract.sample_conditions))
        condition_color = {c: "#" + f"{(0x4060B0 + i * 0x3010):06x}"
                           for i, c in enumerate(unique)}
        for j, c in enumerate(contract.sample_conditions):
            ax.annotate(
                "", xy=(j, -0.06), xytext=(j, -0.02),
                xycoords=("data", "axes fraction"),
                textcoords=("data", "axes fraction"),
                arrowprops=dict(arrowstyle="-", lw=4.5,
                                color=condition_color[c]),
            )
        proxies = [Patch(facecolor=condition_color[c], edgecolor="none", label=c)
                   for c in unique]
        ax.legend(handles=proxies, loc="upper center",
                  bbox_to_anchor=(0.5, 1.12), ncol=len(unique),
                  fontsize=6.6, frameon=False, handlelength=1.0,
                  columnspacing=1.2)

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.03, pad=0.04)
    cbar.set_label("eigengene (z)", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)

    ax.text(0.01, -0.16,
            f"N modules = {len(contract.module_names)}   "
            f"N samples = {len(contract.sample_names)}   "
            f"max |z| = {smart_fmt(float(np.abs(M).max()))}",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.2, color="#333333",
            bbox=dict(boxstyle="round,pad=0.18", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)
    return ax
