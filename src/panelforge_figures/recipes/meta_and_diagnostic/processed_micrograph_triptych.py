"""Processed micrograph triptych — 3-panel raw → skeleton → zone strip.

Image-anchored recipe: takes 3 image paths and lays them out side-by-side
with title labels. No data binding beyond filesystem image references.
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


class MicrographTriptychInput(RecipeContract):
    panel_a_path: str = Field(description="Path to first micrograph (e.g. raw MIP)")
    panel_b_path: str = Field(description="Path to second micrograph (e.g. skeleton)")
    panel_c_path: str = Field(description="Path to third micrograph (e.g. zone map)")
    panel_a_label: str = "Raw MIP"
    panel_b_label: str = "Skeleton"
    panel_c_label: str = "Zone map"
    title: str = "Processed micrograph triptych"


def _demo() -> MicrographTriptychInput:
    return MicrographTriptychInput(
        panel_a_path="(placeholder)",
        panel_b_path="(placeholder)",
        panel_c_path="(placeholder)",
        title="Raw to skeleton to zone composite",
    )


_META = RecipeMetadata(
    name="processed_micrograph_triptych",
    modality="meta_and_diagnostic",
    family=RecipeFamily.heatmap,
    answers_question="What do the raw, processed, and analytically-segmented images look like side-by-side?",
    required_fields=("panel_a_path", "panel_b_path", "panel_c_path"),
    optional_fields=("panel_a_label", "panel_b_label", "panel_c_label", "title"),
    file_format_hints=("png", "tiff"),
    alternatives_in_modality=(),
)


@register_recipe(metadata=_META, contract=MicrographTriptychInput, demo_contract=_demo)
def render(contract: MicrographTriptychInput, ax=None, **_):
    import matplotlib.image as mpimg
    import matplotlib.pyplot as plt
    import numpy as np

    if ax is None:
        fig, ax = plt.subplots(figsize=(11, 4.2))
    else:
        fig = ax.figure
    AESTHETIC.apply_to_ax(ax)
    ax.axis("off")
    gs = fig.add_gridspec(1, 3, wspace=0.05, left=0.02, right=0.98,
                          top=0.90, bottom=0.05)
    paths = [contract.panel_a_path, contract.panel_b_path, contract.panel_c_path]
    labels = [contract.panel_a_label, contract.panel_b_label, contract.panel_c_label]
    for i, (p, lbl) in enumerate(zip(paths, labels)):
        sub = fig.add_subplot(gs[0, i])
        sub.set_xticks([])
        sub.set_yticks([])
        for s in sub.spines.values():
            s.set_color("#cccccc")
            s.set_linewidth(0.5)
        if p and Path(p).exists():
            try:
                img = mpimg.imread(p)
                sub.imshow(img)
            except Exception:
                sub.imshow(np.full((4, 4), 0.95), cmap="Greys", vmin=0, vmax=1)
                sub.text(0.5, 0.5, f"(image error)\n{p}",
                         ha="center", va="center", fontsize=8.4, color="#999",
                         transform=sub.transAxes)
        else:
            sub.imshow(np.full((4, 4), 0.95), cmap="Greys", vmin=0, vmax=1)
            sub.text(0.5, 0.5, "(placeholder)",
                     ha="center", va="center", fontsize=9.6, color="#aaa",
                     transform=sub.transAxes)
        sub.set_title(lbl, fontsize=9.6, color="#2c3e50")
    fig.suptitle(contract.title, fontsize=9.6, color="#555", y=0.99)
    return ax
