"""Skeleton complexity radar — per-condition polygon over 6-8 topology metrics."""

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


class SkeletonComplexityRadarInput(RecipeContract):
    metric_names: list[str] = Field(..., min_length=3)
    condition_values: dict[str, list[float]] = Field(
        ..., description="condition → per-metric values in [0, 1]"
    )
    threshold: list[float] | None = Field(
        None, description="per-metric complexity threshold (0..1) drawn as reference polygon"
    )
    title: str = "Skeleton complexity radar"


def _demo() -> SkeletonComplexityRadarInput:
    metrics = [
        "n_branches", "Horton-Strahler",
        "tortuosity", "path-length",
        "avg degree", "fractal dim", "asymmetry",
    ]
    return SkeletonComplexityRadarInput(
        metric_names=metrics,
        condition_values={
            "control":  [0.85, 0.78, 0.72, 0.80, 0.68, 0.74, 0.62],
            "mutant":   [0.42, 0.40, 0.55, 0.48, 0.45, 0.38, 0.72],
            "rescue":   [0.72, 0.65, 0.70, 0.75, 0.62, 0.68, 0.64],
        },
        threshold=[0.55, 0.55, 0.55, 0.55, 0.55, 0.55, 0.55],
    )


_META = RecipeMetadata(
    name="skeleton_complexity_radar",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.radar,
    answers_question=(
        "How do 6-8 topology-complexity metrics compare per condition, "
        "viewed together on a normalised polar radar?"
    ),
    required_fields=("metric_names", "condition_values"),
    optional_fields=("threshold", "title"),
    file_format_hints=("csv", "yaml"),
    alternatives_in_modality=(
        "filament_orientation_histogram",
        "topology_ternary_simplex",
    ),
)


@register_recipe(
    metadata=_META,
    contract=SkeletonComplexityRadarInput,
    demo_contract=_demo,
)
def render(contract: SkeletonComplexityRadarInput, ax=None, **_):
    import matplotlib.pyplot as plt

    if ax is None:
        fig = plt.figure(figsize=(4.8, 4.4))
        ax = fig.add_subplot(111, polar=True)
    elif not hasattr(ax, "set_theta_offset"):
        fig = ax.figure
        pos = ax.get_subplotspec()
        ax.remove()
        ax = fig.add_subplot(pos, polar=True)
    AESTHETIC.apply_to_fig(ax.figure)
    palette = get_palette(AESTHETIC.primary_palette)

    metrics = contract.metric_names
    n_m = len(metrics)
    theta = np.linspace(0.0, 2 * np.pi, n_m, endpoint=False)
    theta_closed = np.concatenate([theta, theta[:1]])

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(theta)
    ax.set_xticklabels(metrics, fontsize=6.8)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.25", "0.5", "0.75", "1"], fontsize=6.0, color="#666666")
    ax.set_ylim(0, 1.05)
    ax.spines["polar"].set_color("#BBBBBB")
    ax.grid(color="#DDDDDD", lw=0.5)

    # Threshold reference polygon.
    if contract.threshold is not None:
        t_vals = np.asarray(contract.threshold, float)
        t_closed = np.concatenate([t_vals, t_vals[:1]])
        ax.fill(theta_closed, t_closed, color="#C62828", alpha=0.08, zorder=1)
        ax.plot(theta_closed, t_closed, color="#C62828", lw=0.8,
                ls="--", zorder=2, label="threshold")

    # Per-condition polygons with marker dots.
    legend_parts: list[tuple[str, str, float]] = []
    for i, (cond, vals) in enumerate(contract.condition_values.items()):
        v = np.asarray(vals, float)
        v_closed = np.concatenate([v, v[:1]])
        color = palette[i % len(palette.colors)]
        ax.plot(theta_closed, v_closed, color=color, lw=1.2, zorder=3,
                label=cond)
        ax.fill(theta_closed, v_closed, color=color, alpha=0.15, zorder=2)
        ax.scatter(theta, v, s=22, color=color, edgecolor="white",
                   linewidth=0.8, zorder=4)
        legend_parts.append((cond, color, float(v.mean())))

    ax.set_title(contract.title, fontsize=9.0, pad=14)
    legend_labels = [f"{c}  ($\\mu$={smart_fmt(mu)})" for c, _, mu in legend_parts]
    if contract.threshold is not None:
        legend_labels = ["threshold"] + legend_labels
    handles, _labels = ax.get_legend_handles_labels()
    ax.legend(handles, legend_labels,
              loc="upper center", bbox_to_anchor=(0.5, -0.12),
              fontsize=6.6, ncol=min(len(legend_labels), 4),
              frameon=False, handlelength=1.4)
    return ax
