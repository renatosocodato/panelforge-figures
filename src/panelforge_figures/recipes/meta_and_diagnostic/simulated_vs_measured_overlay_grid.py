"""Simulated vs measured 2×2 overlay grid.

Image-anchored recipe: 4-tile composite of measured/simulated × WT/LI.
"""

from __future__ import annotations

from pathlib import Path

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class SimVsMeasuredGridInput(RecipeContract):
    wt_measured_path: str
    wt_simulated_path: str
    li_measured_path: str
    li_simulated_path: str
    title: str = "Simulated vs measured skeleton overlays"


def _demo() -> SimVsMeasuredGridInput:
    return SimVsMeasuredGridInput(
        wt_measured_path="(placeholder)",
        wt_simulated_path="(placeholder)",
        li_measured_path="(placeholder)",
        li_simulated_path="(placeholder)",
    )


_META = RecipeMetadata(
    name="simulated_vs_measured_overlay_grid",
    modality="meta_and_diagnostic",
    family=RecipeFamily.matrix,
    answers_question="How do simulated and measured skeletons compare across genotypes?",
    required_fields=("wt_measured_path", "wt_simulated_path",
                     "li_measured_path", "li_simulated_path"),
    optional_fields=("title",),
    file_format_hints=("png", "tiff"),
    alternatives_in_modality=(),
)


@register_recipe(metadata=_META, contract=SimVsMeasuredGridInput, demo_contract=_demo)
def render(contract: SimVsMeasuredGridInput, ax=None, **_):
    import matplotlib.image as mpimg
    import matplotlib.pyplot as plt

    if ax is None:
        fig, ax = plt.subplots(figsize=(7.5, 7.5))
    else:
        fig = ax.figure
    AESTHETIC.apply_to_ax(ax)
    ax.axis("off")
    gs = fig.add_gridspec(2, 2, hspace=0.10, wspace=0.06,
                          left=0.04, right=0.96, top=0.92, bottom=0.04)
    tiles = [
        (contract.wt_measured_path, "WT measured"),
        (contract.wt_simulated_path, "WT simulated"),
        (contract.li_measured_path, "LI measured"),
        (contract.li_simulated_path, "LI simulated"),
    ]
    for i, (p, lbl) in enumerate(tiles):
        r, c = divmod(i, 2)
        sub = fig.add_subplot(gs[r, c])
        sub.set_xticks([])
        sub.set_yticks([])
        for s in sub.spines.values():
            s.set_color("#bbbbbb")
            s.set_linewidth(0.5)
        if p and Path(p).exists():
            try:
                sub.imshow(mpimg.imread(p))
            except Exception:
                import numpy as np
                sub.imshow(np.full((4, 4), 0.95), cmap="Greys", vmin=0, vmax=1)
                sub.text(0.5, 0.5, "(image error)", ha="center", va="center",
                         fontsize=9.6, color="#999", transform=sub.transAxes)
        else:
            import numpy as np
            sub.imshow(np.full((4, 4), 0.97), cmap="Greys", vmin=0, vmax=1)
            sub.text(0.5, 0.5, "(placeholder)", ha="center", va="center",
                     fontsize=9.6, color="#aaa", transform=sub.transAxes)
        sub.set_title(lbl, fontsize=9.6, color="#2c3e50")
    fig.suptitle(contract.title, fontsize=9.6, color="#555", y=0.99)
    return ax
