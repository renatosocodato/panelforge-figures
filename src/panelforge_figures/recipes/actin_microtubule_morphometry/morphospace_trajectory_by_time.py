"""Morphospace trajectory — per-condition centroid paths through time."""

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


class MorphospaceTrajectoryInput(RecipeContract):
    times: list[float] = Field(...)
    trajectories_by_condition: dict[str, dict[str, list[float]]] = Field(
        ..., description="condition → {'x': [...], 'y': [...]} centroid over time"
    )
    embedding_method: str = "pca"
    cloud_x: list[float] | None = Field(
        None, description="optional per-cell backdrop cloud x"
    )
    cloud_y: list[float] | None = None
    title: str = "Morphospace trajectory"


def _demo() -> MorphospaceTrajectoryInput:
    rng = np.random.default_rng(759)
    times = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    trajs: dict[str, dict[str, list[float]]] = {}
    trajs["control"] = {
        "x": [-2.3, -2.1, -1.9, -1.85, -1.9, -2.0],
        "y": [0.8, 0.9, 1.0, 0.95, 0.9, 0.85],
    }
    trajs["mutant"] = {
        "x": [-1.8, -0.9, 0.1, 1.0, 1.8, 2.3],
        "y": [0.5, 0.1, -0.3, -0.6, -0.9, -1.1],
    }
    trajs["rescue"] = {
        "x": [-2.0, -1.7, -1.4, -1.3, -1.4, -1.5],
        "y": [0.7, 0.55, 0.4, 0.3, 0.35, 0.4],
    }
    # Backdrop cloud (all cells across all timepoints).
    cloud_x = rng.normal(0, 1.6, 260).tolist()
    cloud_y = rng.normal(0, 1.2, 260).tolist()
    return MorphospaceTrajectoryInput(
        times=times,
        trajectories_by_condition=trajs,
        embedding_method="pca",
        cloud_x=cloud_x,
        cloud_y=cloud_y,
    )


_META = RecipeMetadata(
    name="morphospace_trajectory_by_time",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "How does each condition's centroid in shape space move over time?"
    ),
    required_fields=("times", "trajectories_by_condition"),
    optional_fields=("embedding_method", "cloud_x", "cloud_y", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("shape_umap_by_condition",),
)


@register_recipe(
    metadata=_META,
    contract=MorphospaceTrajectoryInput,
    demo_contract=_demo,
)
def render(contract: MorphospaceTrajectoryInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.8))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    # Faint backdrop cloud.
    if contract.cloud_x is not None and contract.cloud_y is not None:
        ax.scatter(contract.cloud_x, contract.cloud_y, s=4,
                   color="#BBBBBB", alpha=0.35, edgecolor="none", zorder=2)

    times = np.asarray(contract.times, float)
    total_time = float(times[-1] - times[0]) if len(times) > 1 else 1.0

    for i, (name, traj) in enumerate(contract.trajectories_by_condition.items()):
        xs = np.asarray(traj["x"], float)
        ys = np.asarray(traj["y"], float)
        color = palette[i % len(palette.colors)]
        # Path with arrowheads mid-way between consecutive points.
        ax.plot(xs, ys, color=color, lw=1.5, zorder=4, label=name,
                solid_capstyle="round")
        for k in range(len(xs) - 1):
            mx = 0.5 * (xs[k] + xs[k + 1])
            my = 0.5 * (ys[k] + ys[k + 1])
            dx = xs[k + 1] - xs[k]
            dy = ys[k + 1] - ys[k]
            ax.annotate("",
                        xy=(mx + dx * 0.15, my + dy * 0.15),
                        xytext=(mx - dx * 0.15, my - dy * 0.15),
                        arrowprops=dict(arrowstyle="->", color=color,
                                        lw=1.1, shrinkA=0, shrinkB=0),
                        zorder=5)
        # Start marker (white fill) + end marker (star).
        ax.scatter([xs[0]], [ys[0]], s=56, facecolor="white",
                   edgecolor=color, linewidth=1.3, zorder=6)
        ax.scatter([xs[-1]], [ys[-1]], s=80, facecolor=color,
                   edgecolor="white", linewidth=1.2, marker="*", zorder=7)
        # Per-timepoint markers.
        ax.scatter(xs, ys, s=18, color=color, edgecolor="white",
                   linewidth=0.5, zorder=4, alpha=0.75)
        # Net displacement callout.
        disp = float(np.sqrt((xs[-1] - xs[0]) ** 2 + (ys[-1] - ys[0]) ** 2))
        ax.annotate(
            f"$\\Delta$ = {smart_fmt(disp)}",
            xy=(xs[-1], ys[-1]),
            xytext=(8, 4), textcoords="offset points",
            fontsize=6.2, color=color,
            bbox=dict(boxstyle="round,pad=0.14", fc="white",
                      ec="none", alpha=0.9),
            zorder=8,
        )

    method = contract.embedding_method.upper()
    ax.set_xlabel(f"{method} 1")
    ax.set_ylabel(f"{method} 2")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(
        f"{contract.title}  ·  {method},  "
        f"T = {smart_fmt(total_time)}",
        fontsize=9.0, pad=4,
    )
    ax.legend(fontsize=6.8, frameon=False, loc="upper left",
              handlelength=1.4)
    return ax
