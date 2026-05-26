"""Forward-simulation snapshot pair — two genotype-projected sim outputs.

Used to display a pair of forward-simulation projection snapshots (typically
xy + xz projections per genotype) stacked vertically with genotype color-bars
and an optional replicate-count annotation.

Image-anchored recipe: takes two PNG paths and renders them as a vertical
pair with consistent genotype framing.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class ForwardSimSnapshotPairInput(RecipeContract):
    wt_snapshot_path: str = Field(description="Path to WT simulation snapshot PNG")
    li_snapshot_path: str = Field(description="Path to LI simulation snapshot PNG")
    wt_label: str = "WT"
    li_label: str = "LI"
    n_replicates_per_genotype: int | None = Field(
        default=None, description="Optional replicate-count annotation"
    )
    title: str = "Forward-simulation snapshots"


def _demo() -> ForwardSimSnapshotPairInput:
    return ForwardSimSnapshotPairInput(
        wt_snapshot_path="(placeholder)",
        li_snapshot_path="(placeholder)",
        n_replicates_per_genotype=256,
        title="Forward3D quasi-3D simulation snapshots — WT vs LI",
    )


_META = RecipeMetadata(
    name="forward_simulation_snapshot_pair",
    modality="meta_and_diagnostic",
    family=RecipeFamily.matrix,
    answers_question="What do the forward-simulation outputs look like per genotype?",
    required_fields=("wt_snapshot_path", "li_snapshot_path"),
    optional_fields=("wt_label", "li_label", "n_replicates_per_genotype", "title"),
    file_format_hints=("png", "tiff"),
    alternatives_in_modality=("simulated_vs_measured_overlay_grid",),
)


@register_recipe(metadata=_META, contract=ForwardSimSnapshotPairInput, demo_contract=_demo)
def render(contract: ForwardSimSnapshotPairInput, ax=None, **_):
    import matplotlib.image as mpimg
    import matplotlib.patches as mpatches
    import matplotlib.pyplot as plt

    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 7))
    else:
        fig = ax.figure
    AESTHETIC.apply_to_ax(ax)
    ax.axis("off")

    # Two-row layout: WT on top, LI on bottom; narrow color-bar on the left
    gs = fig.add_gridspec(2, 2, width_ratios=[0.025, 1.0], wspace=0.012, hspace=0.12,
                          left=0.04, right=0.98, top=0.92, bottom=0.04)

    for ri, (path, label, color) in enumerate([
        (contract.wt_snapshot_path, contract.wt_label, "#1f6f8b"),
        (contract.li_snapshot_path, contract.li_label, "#c0392b"),
    ]):
        ax_bar = fig.add_subplot(gs[ri, 0])
        ax_img = fig.add_subplot(gs[ri, 1])
        ax_bar.add_patch(mpatches.Rectangle((0, 0), 1, 1, facecolor=color,
                                             edgecolor="white", linewidth=0))
        ax_bar.text(0.5, 0.5, label, ha="center", va="center",
                    fontsize=9.6, fontweight="bold", color="white",
                    rotation=90)
        ax_bar.set_xlim(0, 1)
        ax_bar.set_ylim(0, 1)
        ax_bar.set_xticks([])
        ax_bar.set_yticks([])
        for s in ax_bar.spines.values():
            s.set_visible(False)

        ax_img.set_xticks([])

        ax_img.set_yticks([])
        for s in ax_img.spines.values():
            s.set_color("#cccccc")
            s.set_linewidth(0.5)

        p = Path(path) if path else None
        if p and p.exists():
            try:
                ax_img.imshow(mpimg.imread(p))
            except Exception as e:
                import numpy as np
                ax_img.imshow(np.full((4, 4), 0.95), cmap="Greys", vmin=0, vmax=1)
                ax_img.text(0.5, 0.5, f"(image error: {str(e)[:40]})",
                            ha="center", va="center", fontsize=8.4, color="#999",
                            transform=ax_img.transAxes)
        else:
            import numpy as np
            ax_img.imshow(np.full((4, 4), 0.97), cmap="Greys", vmin=0, vmax=1)
            ax_img.set_facecolor("#fafafa")
            ax_img.text(0.5, 0.5, "(snapshot not found)", ha="center", va="center",
                        fontsize=9.6, color="#aaa", transform=ax_img.transAxes)

    title = contract.title
    if contract.n_replicates_per_genotype:
        title = f"{title}  ·  n = {contract.n_replicates_per_genotype} replicates / genotype"
    fig.suptitle(title, fontsize=9.6, color="#2c3e50", y=0.97)
    return ax
