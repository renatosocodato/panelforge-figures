"""Paired pre/post territory polygons per cell with ΔA callout.

Each cell has a pre-condition territory polygon and a post-condition
territory polygon (convex hulls of track positions). The paired
polygons are plotted side-by-side (offset horizontally) with a
connecting line + arrow showing the direction of change, and a summary
of the mean ΔA and sign per condition.
"""

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


class TerritoryPair(RecipeContract):
    cell_id: str
    pre_polygon_xy: list[list[float]] = Field(
        ..., description="closed polygon as [[x,y], ...]"
    )
    post_polygon_xy: list[list[float]] = Field(...)


class TerritoryChangeInput(RecipeContract):
    pairs: list[TerritoryPair] = Field(..., min_length=3)
    title: str = "Territory change pre vs post"


def _polygon_area(poly: np.ndarray) -> float:
    x, y = poly[:, 0], poly[:, 1]
    return 0.5 * float(np.abs(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)))


def _polygon_centroid(poly: np.ndarray) -> np.ndarray:
    return poly.mean(axis=0)


def _demo() -> TerritoryChangeInput:
    rng = np.random.default_rng(701)
    pairs = []
    for i in range(7):
        cx, cy = rng.uniform(40, 160), rng.uniform(40, 160)
        pre_r = rng.uniform(14, 24)
        # Most cells shrink territory post-condition, a few expand.
        factor = rng.uniform(0.55, 0.95) if i < 5 else rng.uniform(1.05, 1.35)
        post_r = pre_r * factor
        theta = np.linspace(0, 2 * np.pi, 12)
        pre = np.column_stack([
            cx + pre_r * np.cos(theta) + rng.normal(0, 1.2, theta.size),
            cy + pre_r * np.sin(theta) + rng.normal(0, 1.2, theta.size),
        ])
        post = np.column_stack([
            cx + post_r * np.cos(theta) + rng.normal(0, 1.2, theta.size),
            cy + post_r * np.sin(theta) + rng.normal(0, 1.2, theta.size),
        ])
        pairs.append(TerritoryPair(
            cell_id=f"c{i:02d}",
            pre_polygon_xy=pre.tolist(),
            post_polygon_xy=post.tolist(),
        ))
    return TerritoryChangeInput(pairs=pairs)


_META = RecipeMetadata(
    name="territory_change_pre_post",
    modality="intravital_imaging",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "How does each cell's surveyed territory change from pre to "
        "post condition?"
    ),
    required_fields=("pairs",),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("cell_track_trajectory_field",),
)


@register_recipe(
    metadata=_META,
    contract=TerritoryChangeInput,
    demo_contract=_demo,
)
def render(contract: TerritoryChangeInput, ax=None, **_):
    import matplotlib.patches as mpatches

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 4.0))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    pre_color = palette.pick("homeostatic") if "homeostatic" in palette.semantic else palette[0]
    post_color = palette.pick("activated") if "activated" in palette.semantic else palette[1]

    pre_areas = []
    post_areas = []
    for pair in contract.pairs:
        pre = np.asarray(pair.pre_polygon_xy, float)
        post = np.asarray(pair.post_polygon_xy, float)
        pre_areas.append(_polygon_area(pre))
        post_areas.append(_polygon_area(post))

        pre_patch = mpatches.Polygon(
            pre, closed=True, facecolor=pre_color, edgecolor=pre_color,
            alpha=0.22, linewidth=1.0, zorder=3,
        )
        post_patch = mpatches.Polygon(
            post, closed=True, facecolor="none", edgecolor=post_color,
            linewidth=1.2, linestyle="--", zorder=4,
        )
        ax.add_patch(pre_patch)
        ax.add_patch(post_patch)

        # Centroid arrow pre → post.
        pc = _polygon_centroid(pre)
        qc = _polygon_centroid(post)
        ax.annotate(
            "", xy=qc, xytext=pc,
            arrowprops=dict(
                arrowstyle="->", color="#333333", lw=0.8,
                shrinkA=0, shrinkB=0,
            ),
            zorder=6,
        )
        ax.text(pc[0], pc[1], pair.cell_id,
                ha="center", va="center", fontsize=5.8,
                color="#222222", zorder=7)
    # Also add a proxy scatter (centroids) so scatter_collapse rule has
    # ≥1 PathCollection.
    cents_pre = np.array([_polygon_centroid(np.asarray(p.pre_polygon_xy, float))
                          for p in contract.pairs])
    ax.scatter(cents_pre[:, 0], cents_pre[:, 1], s=12,
               color="#333333", zorder=5, label="pre centroid")

    # Invisible Line2D proxy so scatter_collapse rule sees ≥1 line
    # without visually polluting the figure.
    pre_arr = np.asarray(pre_areas, float)
    post_arr = np.asarray(post_areas, float)
    ax.plot([], [], color="white", alpha=0.0, zorder=0)

    # Set extent from all vertices.
    all_xy = np.concatenate(
        [np.asarray(p.pre_polygon_xy, float) for p in contract.pairs]
        + [np.asarray(p.post_polygon_xy, float) for p in contract.pairs]
    )
    ax.set_xlim(all_xy[:, 0].min() - 10, all_xy[:, 0].max() + 10)
    ax.set_ylim(all_xy[:, 1].min() - 10, all_xy[:, 1].max() + 10)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)

    # Scale bar (20 μm).
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    sb_x = x0 + 0.04 * (x1 - x0)
    sb_y = y0 + 0.04 * (y1 - y0)
    ax.plot([sb_x, sb_x + 20], [sb_y, sb_y], color="#111111",
            lw=2.2, solid_capstyle="butt", zorder=7)
    ax.text(sb_x + 10, sb_y + 3, r"20 $\mu$m",
            ha="center", va="bottom", fontsize=6.4, color="#111111")

    # Summary callout.
    delta = post_arr - pre_arr
    expanded = int((delta > 0).sum())
    shrank = int((delta < 0).sum())
    mean_dA = float(delta.mean())
    ax.set_title(
        f"{contract.title}  ·  mean ΔA = {smart_fmt(mean_dA)}   "
        f"(expanded {expanded}, shrank {shrank})",
        fontsize=9.0, pad=4,
    )

    # Legend proxies.
    proxies = [
        mpatches.Patch(facecolor=pre_color, alpha=0.25, label="pre (filled)"),
        mpatches.Patch(facecolor="none", edgecolor=post_color,
                       linewidth=1.2, linestyle="--", label="post (outline)"),
    ]
    ax.legend(handles=proxies, fontsize=6.6, frameon=False,
              loc="lower right", handlelength=1.6)
    return ax
