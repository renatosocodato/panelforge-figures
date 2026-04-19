"""2D class averages montage — grid of class-average thumbnails with population labels."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class ClassMontageInput(RecipeContract):
    class_averages: list[list[list[float]]] = Field(
        ..., description="list of 2D arrays (one per class)",
    )
    class_populations: list[int] = Field(...)
    title: str = "2D class averages"


def _demo() -> ClassMontageInput:
    rng = np.random.default_rng(449)
    n_classes = 12
    H, W = 48, 48
    averages = []
    pops = []
    for k in range(n_classes):
        yy, xx = np.mgrid[:H, :W]
        # Fake particle: two Gaussians at random offsets.
        dx = rng.integers(-4, 5)
        dy = rng.integers(-4, 5)
        img = np.exp(-((xx - W // 2 - dx) ** 2 + (yy - H // 2 - dy) ** 2) / 30.0)
        img += 0.6 * np.exp(-((xx - W // 2 + dx) ** 2
                              + (yy - H // 2 + dy - 4) ** 2) / 20.0)
        img += rng.normal(0, 0.04, (H, W))
        averages.append(img.tolist())
        pops.append(int(rng.integers(800, 12000)))
    return ClassMontageInput(
        class_averages=averages,
        class_populations=pops,
    )


_META = RecipeMetadata(
    name="particle_2d_class_montage",
    modality="cryoem_and_structure",
    family=RecipeFamily.matrix,
    answers_question="What are the 2D class-average appearances of the particles, and how are particles distributed across classes?",
    required_fields=("class_averages", "class_populations"),
    optional_fields=("title",),
    file_format_hints=("mrcs", "npz"),
    alternatives_in_modality=("angular_distribution_hist",),
)


@register_recipe(metadata=_META, contract=ClassMontageInput, demo_contract=_demo)
def render(contract: ClassMontageInput, ax=None, **_):
    import matplotlib.pyplot as plt

    n = len(contract.class_averages)
    ncols = 4
    nrows = (n + ncols - 1) // ncols

    if ax is None:
        fig = plt.figure(figsize=(5.0, 3.6))
        gs = fig.add_gridspec(nrows, ncols, wspace=0.08, hspace=0.18)
        axes = [fig.add_subplot(gs[r, c])
                for r in range(nrows) for c in range(ncols)]
    else:
        fig = ax.figure
        pos = ax.get_subplotspec()
        ax.remove()
        sub = pos.subgridspec(nrows, ncols, wspace=0.08, hspace=0.18)
        axes = [fig.add_subplot(sub[r, c])
                for r in range(nrows) for c in range(ncols)]
    AESTHETIC.apply_to_fig(fig)
    for ai in axes:
        AESTHETIC.apply_to_ax(ai)

    total = sum(contract.class_populations)
    for k, ai in enumerate(axes):
        if k >= n:
            ai.axis("off")
            continue
        img = np.array(contract.class_averages[k], dtype=float)
        ai.imshow(img, cmap="gray_r", aspect="equal",
                  interpolation="bilinear")
        ai.set_xticks([])
        ai.set_yticks([])
        for side in ("top", "right", "left", "bottom"):
            ai.spines[side].set_visible(False)
        pop = contract.class_populations[k]
        pct = 100 * pop / max(total, 1)
        ai.text(0.03, 0.96, f"{k + 1}", transform=ai.transAxes,
                ha="left", va="top", fontsize=6.4, color="white",
                bbox=dict(boxstyle="round,pad=0.14", fc="#333333",
                          ec="none", alpha=0.8))
        ai.text(0.5, -0.04,
                f"n={pop:,} ({pct:.1f}%)",
                transform=ai.transAxes,
                ha="center", va="top", fontsize=5.8, color="#444444")

    fig.suptitle(
        f"{contract.title}  ·  {n} classes,  {total:,} particles total",
        fontsize=9.0, y=0.99,
    )
    return axes[0]
