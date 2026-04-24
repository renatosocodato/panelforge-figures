"""HMM state-dwell distribution — per-state dwell time distributions
(time spent in each state before switching) as stacked ridges, with
mean-dwell markers and exponential reference.

Distinct from `track_persistence_hist` (spatial path persistence
length, not state-temporal dwell).
"""

from __future__ import annotations

import numpy as np
from pydantic import Field
from scipy.stats import gaussian_kde

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class HMMDwellInput(RecipeContract):
    dwells_by_state: dict[str, list[float]] = Field(
        ..., description="state name → list of dwell times (seconds)"
    )
    title: str = "HMM state dwell distribution"


def _demo() -> HMMDwellInput:
    rng = np.random.default_rng(1931)
    return HMMDwellInput(
        dwells_by_state={
            "confined": rng.exponential(1.2, 400).tolist(),
            "free":     rng.exponential(0.5, 400).tolist(),
            "directed": rng.exponential(0.8, 400).tolist(),
        },
    )


_META = RecipeMetadata(
    name="hmm_state_dwell_distribution",
    modality="diffusion_and_tracking",
    family=RecipeFamily.ridge_by_group,
    answers_question=(
        "How long do tracks dwell in each HMM-classified state before "
        "switching to another?"
    ),
    required_fields=("dwells_by_state",),
    optional_fields=("title",),
    file_format_hints=("csv",),
    alternatives_in_modality=("track_persistence_hist",),
)


@register_recipe(
    metadata=_META,
    contract=HMMDwellInput,
    demo_contract=_demo,
)
def render(contract: HMMDwellInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.6))
    AESTHETIC.apply_to_ax(ax)

    state_colors = ["#1565C0", "#2E7D32", "#C62828", "#6A1B9A", "#E65100"]
    states = list(contract.dwells_by_state.keys())
    all_vals = np.concatenate([
        np.asarray(contract.dwells_by_state[s], float) for s in states
    ])
    xg = np.linspace(0.0, float(np.percentile(all_vals, 98)), 240)

    kdes = {s: gaussian_kde(np.asarray(contract.dwells_by_state[s], float))
            for s in states}
    max_d = max(k(xg).max() for k in kdes.values())

    y_step = 1.0
    for i, s in enumerate(states[::-1]):
        color = state_colors[(len(states) - 1 - i) % len(state_colors)]
        vals = np.asarray(contract.dwells_by_state[s], float)
        dens = kdes[s](xg)
        dens_s = (dens / max_d) * 0.85 * y_step
        y_base = i * y_step
        ax.fill_between(xg, y_base, y_base + dens_s, color=color,
                        alpha=0.55, linewidth=0, zorder=3)
        ax.plot(xg, y_base + dens_s, color=color, lw=0.8, zorder=4)

        mean_d = float(np.mean(vals))
        med_d = float(np.median(vals))
        # Exponential reference with the same mean.
        exp_ref = (1.0 / mean_d) * np.exp(-xg / mean_d)
        exp_s = (exp_ref / max_d) * 0.85 * y_step
        ax.plot(xg, y_base + exp_s, color="#444444", lw=0.5, ls="--",
                zorder=5)

        # Mean marker.
        ax.scatter([mean_d], [y_base + 0.08],
                   s=22, marker="v", color=color,
                   edgecolor="white", linewidth=0.4, zorder=6)

        ax.text(xg[0], y_base + 0.45 * y_step, s,
                ha="left", va="center", fontsize=7.0, color="#222222")
        ax.text(xg[-1] * 0.98, y_base + 0.82 * y_step,
                f"mean τ = {smart_fmt(mean_d)} s  med {smart_fmt(med_d)}",
                ha="right", va="top", fontsize=6.4, color=color)

    ax.set_xlim(0, xg.max())
    ax.set_ylim(-0.3, len(states) - 0.1)
    ax.set_yticks([])
    ax.set_xlabel("dwell time τ (s)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    for side in ("left",):
        ax.spines[side].set_visible(False)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
