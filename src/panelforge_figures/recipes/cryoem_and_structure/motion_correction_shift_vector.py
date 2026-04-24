"""Motion-correction shift-vector quiver — per-frame (dx, dy) shifts
from a reference origin with cumulative-drift annotation.

Conceptual family: ≥3 text labels + ≥2 patches.
"""

from __future__ import annotations

import numpy as np
import matplotlib.patches as mpatches
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class MotionShiftInput(RecipeContract):
    frame_index: list[int] = Field(..., min_length=5)
    dx: list[float] = Field(..., description="per-frame x-shift (Å)")
    dy: list[float] = Field(..., description="per-frame y-shift (Å)")
    dose_per_frame: float = Field(
        1.0, description="electron dose per frame (e-/Å²)"
    )
    title: str = "Motion-correction shifts"


def _demo() -> MotionShiftInput:
    rng = np.random.default_rng(3411)
    n = 40
    # First-frame large drift, later frames small; superimposed jitter.
    t = np.arange(n)
    dx = 0.8 * np.exp(-t / 6) - 0.25 + rng.normal(0, 0.08, n)
    dy = 0.6 * np.exp(-t / 5) + 0.15 + rng.normal(0, 0.08, n)
    # Make it a cumulative drift: cumsum of per-frame shifts.
    dx_cum = np.cumsum(dx * 0.4)
    dy_cum = np.cumsum(dy * 0.4)
    return MotionShiftInput(
        frame_index=t.tolist(),
        dx=dx_cum.tolist(),
        dy=dy_cum.tolist(),
        dose_per_frame=1.2,
    )


_META = RecipeMetadata(
    name="motion_correction_shift_vector",
    modality="cryoem_and_structure",
    family=RecipeFamily.conceptual,
    answers_question=(
        "Per movie frame, how large and correlated were the motion-"
        "correction shifts?"
    ),
    required_fields=("frame_index", "dx", "dy"),
    optional_fields=("dose_per_frame", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("angular_distribution_hist",),
)


@register_recipe(
    metadata=_META,
    contract=MotionShiftInput,
    demo_contract=_demo,
)
def render(contract: MotionShiftInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 4.2))
    AESTHETIC.apply_to_ax(ax)

    frames = np.asarray(contract.frame_index, float)
    dx = np.asarray(contract.dx, float)
    dy = np.asarray(contract.dy, float)

    # Plot trajectory as connected line + markers coloured by frame.
    scatter = ax.scatter(dx, dy, c=frames, cmap="viridis",
                         s=32, edgecolor="white", linewidth=0.5,
                         zorder=5)
    ax.plot(dx, dy, color="#777777", lw=0.7, alpha=0.7, zorder=3)

    # Compute a scale for label offsets based on data extent.
    lim = float(max(abs(dx).max(), abs(dy).max())) * 1.25 + 0.1
    offset = lim * 0.06

    # Origin marker — label below-left to stay clear of frame-0.
    ax.add_patch(mpatches.Circle(
        (0, 0), offset * 0.5,
        facecolor="#222222", edgecolor="white",
        linewidth=0.8, zorder=6,
    ))
    ax.text(-offset, -offset, "origin",
            ha="right", va="top", fontsize=6.6,
            color="#333333", zorder=7)

    # First and last frame markers — labels offset so they don't
    # stack on the origin or each other.
    ax.add_patch(mpatches.Circle(
        (float(dx[0]), float(dy[0])), offset * 0.6,
        facecolor="none", edgecolor="#2E7D32", linewidth=1.2,
        zorder=7,
    ))
    ax.text(float(dx[0]) + offset, float(dy[0]) - offset,
            "frame 0", ha="left", va="top",
            fontsize=6.4, color="#2E7D32", zorder=7)
    ax.add_patch(mpatches.Circle(
        (float(dx[-1]), float(dy[-1])), offset * 0.6,
        facecolor="none", edgecolor="#C62828", linewidth=1.2,
        zorder=7,
    ))
    ax.text(float(dx[-1]) + offset, float(dy[-1]) + offset,
            f"frame {int(frames[-1])}",
            ha="left", va="bottom",
            fontsize=6.4, color="#C62828", zorder=7)

    # Crosshair at origin.
    ax.axhline(0, color="#DDDDDD", lw=0.5, zorder=1)
    ax.axvline(0, color="#DDDDDD", lw=0.5, zorder=1)

    cbar = ax.figure.colorbar(scatter, ax=ax, fraction=0.040, pad=0.03)
    cbar.set_label("frame index", fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    # Cumulative-drift metric.
    per_frame_dist = np.sqrt(np.diff(dx) ** 2 + np.diff(dy) ** 2)
    total_path = float(np.sum(per_frame_dist))
    net_disp = float(np.hypot(dx[-1] - dx[0], dy[-1] - dy[0]))
    mean_step = float(np.mean(per_frame_dist)) if per_frame_dist.size else 0.0

    ax.set_aspect("equal")
    ax.set_xlabel("dx (Å)")
    ax.set_ylabel("dy (Å)")

    # Tight limits around the actual data range.
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)

    ax.set_title(
        f"{contract.title}  ·  n_frames = {len(frames)}  ·  "
        f"total path {smart_fmt(total_path)} Å  ·  "
        f"net drift {smart_fmt(net_disp)} Å",
        fontsize=7.8, pad=4,
    )
    ax.text(0.02, 0.97,
            f"dose per frame: {smart_fmt(float(contract.dose_per_frame))} e-/Å²\n"
            f"mean per-frame step: {smart_fmt(mean_step)} Å",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.4, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=7)
    return ax
