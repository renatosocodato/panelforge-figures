"""Per-cell time-above-threshold (oxidized-state duration) survival curves.

Derived quantity: for each cell, the total time spent above a fixed
oxidation threshold during a fixed observation window. Plotted as a
complementary cumulative distribution (survival) per condition with
median-duration markers.

Distinct from `ratio_trajectory_with_phase_annotation` (raw ratio
trajectory per cell) and `single_cell_ratio_distribution` (instantaneous
ratio KDE, not duration).
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


class TimeAboveThresholdInput(RecipeContract):
    durations_by_condition: dict[str, list[float]] = Field(
        ..., description="condition → per-cell duration above threshold (min)"
    )
    observation_window: float = Field(
        default=60.0, description="total observation window (same unit as durations)"
    )
    threshold_label: str = "ratio > 1.3"
    time_label: str = "time (min)"
    title: str = "Time above oxidation threshold"


def _demo() -> TimeAboveThresholdInput:
    rng = np.random.default_rng(277)
    cond = {}
    # baseline: mostly 0, some short events
    cond["baseline"] = np.clip(rng.exponential(2.0, 120), 0, 60).tolist()
    # LPS: broad distribution up to nearly saturation
    cond["LPS"] = np.clip(rng.gamma(3.0, 9.0, 120), 0, 60).tolist()
    # LPS + NAC: rescued back toward baseline
    cond["LPS+NAC"] = np.clip(rng.exponential(6.0, 120), 0, 60).tolist()
    # H2O2: saturates (long)
    cond["H2O2"] = np.clip(rng.gamma(5.0, 8.0, 120), 0, 60).tolist()
    return TimeAboveThresholdInput(
        durations_by_condition=cond,
        observation_window=60.0,
    )


_META = RecipeMetadata(
    name="time_above_threshold_distribution",
    modality="redox_imaging",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "How long do individual cells spend above the oxidation "
        "threshold, and how does that duration distribute per condition?"
    ),
    required_fields=("durations_by_condition",),
    optional_fields=(
        "observation_window", "threshold_label", "time_label", "title",
    ),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=(
        "single_cell_ratio_distribution",
        "ratio_trajectory_with_phase_annotation",
    ),
)


@register_recipe(
    metadata=_META,
    contract=TimeAboveThresholdInput,
    demo_contract=_demo,
)
def render(contract: TimeAboveThresholdInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    conditions = list(contract.durations_by_condition.keys())

    for i, name in enumerate(conditions):
        vals = np.asarray(contract.durations_by_condition[name], float)
        vals = vals[np.isfinite(vals)]
        if vals.size == 0:
            continue
        color = palette[i % len(palette.colors)]
        xs = np.sort(vals)
        # Complementary CDF: P(T > t)
        ccdf = 1.0 - np.arange(1, xs.size + 1) / xs.size
        ax.step(np.concatenate([[0.0], xs]),
                np.concatenate([[1.0], ccdf]),
                where="post", color=color, lw=1.3,
                label=f"{name} (n={xs.size})", zorder=3)
        # Median marker.
        med = float(np.median(vals))
        ax.scatter([med], [0.5], s=30, color=color,
                   edgecolor="white", linewidth=0.7, zorder=4)
        ax.text(med, 0.5, f"  med={smart_fmt(med)}",
                ha="left", va="center", fontsize=6.2, color=color,
                zorder=5)

    # 50 % reference.
    ax.axhline(0.5, color="#888888", lw=0.6, ls="--", zorder=1,
               label="P = 0.5")

    ax.set_xlabel(
        f"{contract.time_label} with {contract.threshold_label}"
    )
    ax.set_ylabel("P(duration > t)")
    ax.set_xlim(0, contract.observation_window)
    ax.set_ylim(0, 1.02)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.6)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
