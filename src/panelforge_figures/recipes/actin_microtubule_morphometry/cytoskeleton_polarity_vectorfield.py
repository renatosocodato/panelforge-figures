"""Cytoskeleton polarity vector field — per-cell polarity arrows across a field."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class PolarityVectorFieldInput(RecipeContract):
    cell_x_um: list[float] = Field(...)
    cell_y_um: list[float] = Field(...)
    polarity_ux: list[float] = Field(...)
    polarity_uy: list[float] = Field(...)
    polarity_magnitude: list[float] = Field(
        ..., description="polarity strength per cell in [0, 1]"
    )
    condition: list[str] | None = None
    extent_um: tuple[float, float, float, float] = (0.0, 200.0, 0.0, 150.0)
    title: str = "Cytoskeleton polarity field"


def _demo() -> PolarityVectorFieldInput:
    rng = np.random.default_rng(825)
    n = 48
    xs = rng.uniform(15, 185, n)
    ys = rng.uniform(12, 138, n)
    # Cells in the upper half polarised rightward; lower half polarised upward.
    theta = np.where(ys > 75, 0.0, np.pi / 2)
    theta += rng.normal(0, 0.35, n)
    mag = rng.beta(4, 2, n)
    ux = mag * np.cos(theta)
    uy = mag * np.sin(theta)
    cond = np.where(ys > 75, "upper", "lower").tolist()
    return PolarityVectorFieldInput(
        cell_x_um=xs.tolist(),
        cell_y_um=ys.tolist(),
        polarity_ux=ux.tolist(),
        polarity_uy=uy.tolist(),
        polarity_magnitude=mag.tolist(),
        condition=cond,
    )


_META = RecipeMetadata(
    name="cytoskeleton_polarity_vectorfield",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.heatmap,
    answers_question=(
        "Across a segmented multi-cell field, where do cells point their "
        "cytoskeletal polarity vectors?"
    ),
    required_fields=(
        "cell_x_um", "cell_y_um",
        "polarity_ux", "polarity_uy", "polarity_magnitude",
    ),
    optional_fields=("condition", "extent_um", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=(
        "mitochondrial_axis_alignment",
        "actin_microtubule_crosstalk_quiver",
    ),
)


@register_recipe(
    metadata=_META,
    contract=PolarityVectorFieldInput,
    demo_contract=_demo,
)
def render(contract: PolarityVectorFieldInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.8))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    xs = np.asarray(contract.cell_x_um, float)
    ys = np.asarray(contract.cell_y_um, float)
    ux = np.asarray(contract.polarity_ux, float)
    uy = np.asarray(contract.polarity_uy, float)
    mag = np.asarray(contract.polarity_magnitude, float)
    cond = (np.asarray(contract.condition)
            if contract.condition is not None
            else np.array(["all"] * xs.size))
    x0, x1, y0, y1 = contract.extent_um

    # Cell-density backdrop (satisfies the heatmap quality rule with a QuadMesh).
    ax.hist2d(
        xs, ys, bins=(36, 27), range=[[x0, x1], [y0, y1]],
        cmap="Greys", cmin=1, alpha=0.35, zorder=1,
    )

    uniques = list(dict.fromkeys(cond.tolist()))
    for i, name in enumerate(uniques):
        m = cond == name
        color = palette[i % len(palette.colors)]
        ax.scatter(xs[m], ys[m], s=20, color=color, alpha=0.85,
                   edgecolor="white", linewidth=0.5, zorder=3,
                   label=f"{name} (n={int(m.sum())})")
        ax.quiver(
            xs[m], ys[m], ux[m], uy[m],
            color=color, angles="xy", scale_units="xy", scale=0.05,
            width=0.0035, headwidth=3.8, headlength=4.4, headaxislength=3.8,
            zorder=4, alpha=0.9,
        )

    # Mean resultant length — polarity "alignment" per condition.
    summary_parts = []
    for name in uniques:
        m = cond == name
        if m.sum() == 0:
            continue
        R = float(np.sqrt(ux[m].mean() ** 2 + uy[m].mean() ** 2))
        summary_parts.append(f"{name}: R = {smart_fmt(R)}")
    ax.text(
        0.02, 0.04, "  ·  ".join(summary_parts),
        transform=ax.transAxes, ha="left", va="bottom",
        fontsize=6.4, color="#333333",
        bbox=dict(boxstyle="round,pad=0.18", fc="white",
                  ec="#BBBBBB", lw=0.5, alpha=0.92),
        zorder=7,
    )

    # Mandatory scale bar (20 µm).
    sb_x, sb_y = x0 + 8, y0 + 6
    ax.plot([sb_x, sb_x + 20], [sb_y, sb_y], color="#111111",
            lw=2.2, solid_capstyle="butt", zorder=6)
    ax.text(sb_x + 10, sb_y + (y1 - y0) * 0.03,
            r"20 $\mu$m",
            ha="center", va="bottom", fontsize=6.2, color="#111111")

    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_title(
        f"{contract.title}  ·  N cells = {xs.size},  "
        f"mean polarity magnitude = {smart_fmt(float(mag.mean()))}",
        fontsize=8.4, pad=4,
    )
    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.4)
    return ax
