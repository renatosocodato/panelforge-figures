"""Contact patch statistics panel — per-cell patch count, size, fragmentation."""

from __future__ import annotations

from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class ContactPatchStatsInput(RecipeContract):
    n_patches_by_group: dict[str, list[int]] = Field(description="group → per-cell patch counts")
    mean_patch_size_um2_by_group: dict[str, list[float]] = Field(description="group → per-cell mean patch size (μm²)")
    fragmentation_by_group: dict[str, list[float]] | None = Field(
        default=None, description="Optional group → per-cell fragmentation index"
    )
    title: str = "Contact patch statistics"


def _demo() -> ContactPatchStatsInput:
    import random
    rng = random.Random(42)
    return ContactPatchStatsInput(
        n_patches_by_group={
            "WT": [rng.randint(2, 6) for _ in range(7)],
            "LI": [rng.randint(4, 12) for _ in range(16)],
        },
        mean_patch_size_um2_by_group={
            "WT": [rng.gauss(8.0, 2.0) for _ in range(7)],
            "LI": [rng.gauss(5.5, 1.5) for _ in range(16)],
        },
        title="Contact patch statistics by genotype",
    )


_META = RecipeMetadata(
    name="contact_patch_statistics_panel",
    modality="spatial_statistics",
    family=RecipeFamily.coef_forest,
    answers_question="How do per-cell contact patch counts and sizes distribute by group?",
    required_fields=("n_patches_by_group", "mean_patch_size_um2_by_group"),
    optional_fields=("fragmentation_by_group", "title"),
    file_format_hints=("csv", "json"),
)


@register_recipe(metadata=_META, contract=ContactPatchStatsInput, demo_contract=_demo)
def render(contract: ContactPatchStatsInput, ax=None, **_):
    import matplotlib.pyplot as plt
    import numpy as np

    if ax is None:
        fig, ax = plt.subplots(figsize=(9, 4.5))
    else:
        fig = ax.figure
    AESTHETIC.apply_to_ax(ax)
    ax.axis("off")
    palette = get_palette(AESTHETIC.primary_palette)

    gs = fig.add_gridspec(1, 2, wspace=0.30, left=0.08, right=0.97,
                          top=0.86, bottom=0.12)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    AESTHETIC.apply_to_ax(ax1)
    AESTHETIC.apply_to_ax(ax2)

    groups = list(contract.n_patches_by_group.keys())
    rng = np.random.default_rng(42)
    for i, g in enumerate(groups):
        c = palette[i]
        n_vals = np.asarray(contract.n_patches_by_group[g], dtype=float)
        s_vals = np.asarray(contract.mean_patch_size_um2_by_group[g], dtype=float)
        for ax_, vals, ylabel in [(ax1, n_vals, "n patches per cell"),
                                   (ax2, s_vals, "mean patch size (μm²)")]:
            x = np.full(len(vals), i) + rng.uniform(-0.12, 0.12, len(vals))
            ax_.scatter(x, vals, s=42, color=c, edgecolor="white",
                        linewidth=0.7, alpha=0.85, label=g if ax_ is ax1 else None)
            ax_.plot([i - 0.2, i + 0.2], [np.median(vals), np.median(vals)], color=c, linewidth=2)
    for ax_, ylabel in [(ax1, "n patches per cell"),
                         (ax2, "mean patch size (μm²)")]:
        ax_.set_xticks(range(len(groups)))
        ax_.set_xticklabels(groups, fontsize=9.6)
        ax_.set_ylabel(ylabel, fontsize=9.0)
        ax_.spines[["top", "right"]].set_visible(False)
    ax1.legend(fontsize=8.4, frameon=False)
    fig.suptitle(contract.title, fontsize=9.6, color="#2c3e50", y=0.97)
    return ax
