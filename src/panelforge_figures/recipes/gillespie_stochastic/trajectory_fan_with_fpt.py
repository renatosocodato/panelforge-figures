"""Trajectory fan — SSA trajectories + first-passage-time markers + mean curve."""

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


class TrajectoryFanInput(RecipeContract):
    t: list[float] = Field(..., description="shared time grid")
    trajectories: list[list[float]] = Field(
        ..., description="one state vector per run, aligned to t"
    )
    fpt_times: list[float] = Field(
        default_factory=list,
        description="first-passage-time per run; same length as trajectories",
    )
    threshold: float = 1.0
    title: str = "SSA trajectories · first passage"


def _demo() -> TrajectoryFanInput:
    rng = np.random.default_rng(103)
    t = np.linspace(0, 40, 400)
    trajs = []
    fpts = []
    for _ in range(30):
        # Biased random walk hitting threshold = 1.0.
        steps = rng.normal(0.01, 0.2, t.size)
        x = np.cumsum(steps)
        trajs.append(x.tolist())
        hit = np.argmax(x >= 1.0)
        fpts.append(float(t[hit]) if x.max() >= 1.0 else float(t[-1]))
    return TrajectoryFanInput(
        t=t.tolist(),
        trajectories=trajs,
        fpt_times=fpts,
        threshold=1.0,
        title="SSA trajectories (30 runs)",
    )


_META = RecipeMetadata(
    name="trajectory_fan_with_fpt",
    modality="gillespie_stochastic",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question="How do individual SSA trajectories fan out over time, and when does each first cross a threshold?",
    required_fields=("t", "trajectories"),
    optional_fields=("fpt_times", "threshold", "title"),
    file_format_hints=("parquet", "npz", "pickle"),
    alternatives_in_modality=("ensemble_mean_variance_tube",),
)


@register_recipe(metadata=_META, contract=TrajectoryFanInput, demo_contract=_demo)
def render(contract: TrajectoryFanInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    t = np.array(contract.t, dtype=float)
    trajs = [np.array(tr, dtype=float) for tr in contract.trajectories]

    # Fan of thin trajectories.
    home = palette.pick("HOME")
    for tr in trajs:
        ax.plot(t, tr, color=home, lw=0.5, alpha=0.25,
                drawstyle="steps-post", zorder=2)

    # Mean envelope.
    if trajs:
        stacked = np.vstack(trajs)
        mean = stacked.mean(axis=0)
        lo = np.quantile(stacked, 0.1, axis=0)
        hi = np.quantile(stacked, 0.9, axis=0)
        ax.fill_between(t, lo, hi, color=home, alpha=0.18,
                        linewidth=0, zorder=3, label="10-90 percentile")
        ax.plot(t, mean, color="#111111", lw=1.2, zorder=5,
                label="ensemble mean")

    # Threshold line.
    ax.axhline(contract.threshold, color="#D32F2F", lw=0.8, ls="--",
               zorder=4, label=f"threshold = {smart_fmt(contract.threshold)}")

    # First-passage markers on the threshold line.
    if contract.fpt_times:
        ax.scatter(contract.fpt_times,
                   [contract.threshold] * len(contract.fpt_times),
                   s=24, marker="*", color="#D32F2F",
                   edgecolor="white", linewidth=0.5, zorder=6)
        mean_fpt = float(np.mean(contract.fpt_times))
        ax.axvline(mean_fpt, color="#D32F2F", lw=0.5, ls=":", zorder=3)
        ax.text(mean_fpt, ax.get_ylim()[1],
                rf"$\langle$FPT$\rangle$ = {smart_fmt(mean_fpt)}",
                ha="center", va="top", fontsize=6.6, color="#D32F2F",
                bbox=dict(boxstyle="round,pad=0.18", fc="white",
                          ec="none", alpha=0.92),
                zorder=7)

    ax.set_xlabel("time")
    ax.set_ylabel("state")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="upper left",
              handlelength=1.8)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Runs counter.
    ax.text(0.99, 0.02,
            f"N runs = {len(trajs)}",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6.4, color="#444444",
            bbox=dict(boxstyle="round,pad=0.20", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=7)
    return ax
