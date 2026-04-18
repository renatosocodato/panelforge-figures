"""QC metric radar — multi-axis polar plot summarizing per-sample QC."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    add_halo_label,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class QCMetricRadarInput(RecipeContract):
    metric_names: list[str] = Field(..., min_length=3)
    sample_values: dict[str, list[float]] = Field(..., description="sample_id → metric values (0..1)")
    threshold: list[float] | None = Field(
        None, description="per-metric pass threshold (0..1); values above pass QC"
    )
    title: str = "QC metric radar"


def _demo() -> QCMetricRadarInput:
    metrics = ["align rate", "duplication", "GC bias", "coverage", "rRNA %", "insert size"]
    return QCMetricRadarInput(
        metric_names=metrics,
        sample_values={
            "S01 (passing)": [0.93, 0.82, 0.88, 0.78, 0.91, 0.86],
            "S02 (borderline)": [0.87, 0.74, 0.52, 0.62, 0.66, 0.70],
            "S03 (failing)": [0.55, 0.41, 0.35, 0.38, 0.30, 0.45],
        },
        threshold=[0.80, 0.70, 0.65, 0.65, 0.60, 0.70],
    )


_META = RecipeMetadata(
    name="qc_metric_radar",
    modality="meta_and_diagnostic",
    family=RecipeFamily.radar,
    answers_question="Which samples pass every QC metric at once versus which fail which axes?",
    required_fields=("metric_names", "sample_values"),
    optional_fields=("threshold", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("missing_data_pattern_matrix",),
)


@register_recipe(metadata=_META, contract=QCMetricRadarInput, demo_contract=_demo)
def render(contract: QCMetricRadarInput, ax=None, **_):
    import matplotlib.pyplot as plt
    if ax is None:
        fig = plt.figure(figsize=(4.6, 4.2))
        ax = fig.add_subplot(111, polar=True)
    elif not hasattr(ax, "set_theta_offset"):
        # Caller gave a cartesian axis; replace it in its grid slot with a polar one.
        fig = ax.figure
        pos = ax.get_subplotspec()
        ax.remove()
        ax = fig.add_subplot(pos, polar=True)

    AESTHETIC.apply_to_fig(ax.figure)
    palette = get_palette(AESTHETIC.primary_palette)
    metrics = contract.metric_names
    n_m = len(metrics)
    theta = np.linspace(0, 2 * np.pi, n_m, endpoint=False)
    theta_closed = np.concatenate([theta, theta[:1]])

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(theta)
    ax.set_xticklabels(metrics, fontsize=6.8)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.25", "0.5", "0.75", "1"], fontsize=6.2, color="#666666")
    ax.set_ylim(0, 1.05)
    ax.spines["polar"].set_color("#BBBBBB")
    ax.grid(color="#DDDDDD", lw=0.5)

    # Threshold polygon (shaded).
    if contract.threshold is not None:
        t = np.array(contract.threshold, dtype=float)
        t_closed = np.concatenate([t, t[:1]])
        ax.fill(theta_closed, t_closed, color="#C62828", alpha=0.10, zorder=1)
        ax.plot(theta_closed, t_closed, color="#C62828", lw=1.0, ls="--", zorder=2)
        add_halo_label(
            ax, theta[0], float(t[0]), "threshold",
            color="#C62828", fontsize=6.4, fontweight="bold",
            halo_width=2.2, ha="left", va="bottom",
        )

    # Per-sample polygons.
    for i, (sample, vals) in enumerate(contract.sample_values.items()):
        v = np.array(vals, dtype=float)
        v_closed = np.concatenate([v, v[:1]])
        color = palette[i]
        ax.plot(theta_closed, v_closed, color=color, lw=1.8, label=sample, zorder=3)
        ax.fill(theta_closed, v_closed, color=color, alpha=0.12, zorder=2)
        # Per-metric halo'd values.
        for k, (tv, vv) in enumerate(zip(theta, v)):
            ax.scatter([tv], [vv], color=color, s=22, edgecolor="white",
                       linewidth=0.8, zorder=4)
        # Overall summary (mean).
        add_halo_label(
            ax, theta[i % n_m], 1.08,
            f"{sample}: μ={smart_fmt(v.mean())}",
            color=color, fontsize=6.4, fontweight="bold", halo_width=2.2,
        )

    ax.set_title(contract.title, fontsize=9.0, fontweight="bold", pad=14)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.18),
              fontsize=6.6, ncol=min(len(contract.sample_values), 3), frameon=False)
    return ax
