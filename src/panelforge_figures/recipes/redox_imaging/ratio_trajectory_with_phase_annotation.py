"""Ratio trajectory with phase annotations — timecourse colored by redox phase."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class RatioTrajInput(RecipeContract):
    t: list[float] = Field(...)
    ratio: list[float] = Field(...)
    phase_spans: list[tuple[float, float, str]] = Field(
        default_factory=list,
        description="(t_start, t_end, phase_label) triplets"
    )
    lower_thr: float = 0.8
    upper_thr: float = 1.2
    title: str = "Ratio trajectory · phase annotations"


def _demo() -> RatioTrajInput:
    rng = np.random.default_rng(151)
    t = np.linspace(0, 120, 600)
    r = 0.9 + 0.08 * np.sin(0.12 * t) + rng.normal(0, 0.04, t.size)
    r[t > 45] += np.tanh((t[t > 45] - 45) / 10) * 0.5       # shift to oxidized
    r[t > 100] -= 0.3                                      # back down
    spans = [
        (0, 45, "reduced"),
        (45, 100, "oxidized"),
        (100, 120, "recovery"),
    ]
    return RatioTrajInput(
        t=t.tolist(),
        ratio=r.tolist(),
        phase_spans=spans,
    )


_META = RecipeMetadata(
    name="ratio_trajectory_with_phase_annotation",
    modality="redox_imaging",
    family=RecipeFamily.diagnostic_curve,
    answers_question="How does the redox ratio change over time, segmented by reduced / oxidized / recovery phases?",
    required_fields=("t", "ratio"),
    optional_fields=("phase_spans", "lower_thr", "upper_thr", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("bistability_hysteresis_loop",),
)


@register_recipe(metadata=_META, contract=RatioTrajInput, demo_contract=_demo)
def render(contract: RatioTrajInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.0))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    t = np.array(contract.t, dtype=float)
    r = np.array(contract.ratio, dtype=float)

    phase_colors = {
        "reduced": palette.pick("reduced"),
        "oxidized": palette.pick("oxidized"),
        "intermediate": palette.pick("intermediate"),
        "recovery": "#A5D6A7",
    }

    # Phase-shaded backgrounds.
    for (t0, t1, name) in contract.phase_spans:
        color = phase_colors.get(name, "#EEEEEE")
        ax.axvspan(t0, t1, color=color, alpha=0.18, zorder=1)
        ax.text((t0 + t1) / 2, ax.get_ylim()[1] if False else 1.55,
                name, ha="center", va="top",
                fontsize=6.6, color=color,
                bbox=dict(boxstyle="round,pad=0.14", fc="white",
                          ec="none", alpha=0.9),
                zorder=6)

    # Thresholds.
    ax.axhline(contract.lower_thr, color="#888888", lw=0.5, ls=":", zorder=2)
    ax.axhline(contract.upper_thr, color="#888888", lw=0.5, ls=":", zorder=2)
    ax.axhline(1.0, color="#555555", lw=0.6, ls="--", zorder=2,
               label="ratio = 1")

    # Trajectory.
    ax.plot(t, r, color="#222222", lw=1.2, zorder=4, label="ratio(t)")

    ax.set_xlabel("time (s)")
    ax.set_ylabel("redox ratio")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="lower right",
              handlelength=1.8)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
