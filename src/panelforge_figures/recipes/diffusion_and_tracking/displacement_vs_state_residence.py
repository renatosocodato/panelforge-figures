"""Displacement vs state-residence matrix — heatmap of next-step |Δr|
conditional on how long a track has resided in a state before that step.

Axis grammar: **residence-time bin × state** heatmap (state rows,
residence-bin columns), with per-state median-|Δr| curve overlaid.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class DispStateResInput(RecipeContract):
    state_names: list[str] = Field(..., min_length=2)
    residence_bins_s: list[float] = Field(
        ..., min_length=3,
        description="residence-time bin edges (seconds), length n_bins+1",
    )
    median_displacement: list[list[float]] = Field(
        ...,
        description="n_states × n_bins median |Δr| in μm",
    )
    title: str = "Displacement vs state-residence"


def _demo() -> DispStateResInput:
    rng = np.random.default_rng(2017)
    states = ["confined", "free", "directed"]
    bins = [0.0, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4]
    n_states = len(states)
    n_bins = len(bins) - 1
    # Expected: confined Δr decreases with residence (deeper trap),
    # free approximately constant, directed increasing (commitment).
    M = np.zeros((n_states, n_bins))
    M[0] = np.linspace(0.10, 0.04, n_bins) * np.exp(rng.normal(0, 0.05, n_bins))
    M[1] = np.linspace(0.21, 0.23, n_bins) * np.exp(rng.normal(0, 0.05, n_bins))
    M[2] = np.linspace(0.18, 0.38, n_bins) * np.exp(rng.normal(0, 0.05, n_bins))
    return DispStateResInput(
        state_names=states,
        residence_bins_s=bins,
        median_displacement=M.tolist(),
    )


_META = RecipeMetadata(
    name="displacement_vs_state_residence",
    modality="diffusion_and_tracking",
    family=RecipeFamily.matrix,
    answers_question=(
        "Conditional on how long a track has resided in a state, how "
        "does the next-step displacement distribution shift?"
    ),
    required_fields=(
        "state_names", "residence_bins_s", "median_displacement",
    ),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("hmm_state_dwell_distribution",),
)


@register_recipe(
    metadata=_META,
    contract=DispStateResInput,
    demo_contract=_demo,
)
def render(contract: DispStateResInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.6))
    AESTHETIC.apply_to_ax(ax)

    states = contract.state_names
    bins = np.asarray(contract.residence_bins_s, float)
    M = np.asarray(contract.median_displacement, float)
    n_states, n_bins = M.shape

    # Bin centres on a log-or-linear mid (linear here).
    centres = 0.5 * (bins[:-1] + bins[1:])
    v_hi = float(max(M.max(), 1e-6))

    im = ax.imshow(M, aspect="auto", cmap="viridis",
                   vmin=0, vmax=v_hi,
                   extent=[bins[0], bins[-1], n_states - 0.5, -0.5],
                   interpolation="nearest", zorder=2)

    ax.set_yticks(range(n_states))
    ax.set_yticklabels(states, fontsize=7.0)
    ax.set_xlabel("residence time (s)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.040, pad=0.03)
    cbar.set_label("median |Δr| (μm)", fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    # Per-state trend arrow + summary in-cell labels.
    for s in range(n_states):
        delta = M[s, -1] - M[s, 0]
        arrow = "->" if delta > 0 else ("<-" if delta < 0 else "~")
        ax.text(bins[-1] + 0.04 * (bins[-1] - bins[0]), s,
                f"Δ = {smart_fmt(float(delta))} {arrow}",
                ha="left", va="center", fontsize=6.4,
                color="#333333", zorder=5)
        for j, c in enumerate(centres):
            ax.text(c, s, smart_fmt(float(M[s, j])),
                    ha="center", va="center", fontsize=5.8,
                    color=("white" if M[s, j] > v_hi * 0.55 else "#222222"),
                    zorder=4)

    # Top summary: which state changes most.
    deltas = M[:, -1] - M[:, 0]
    top_idx = int(np.argmax(np.abs(deltas)))
    ax.text(0.02, 1.04,
            f"largest trend: {states[top_idx]}  "
            f"(Δ|Δr| = {smart_fmt(float(deltas[top_idx]))} μm)",
            transform=ax.transAxes, ha="left", va="bottom",
            fontsize=6.4, color="#333333", zorder=6)

    ax.set_xlim(bins[0], bins[-1])
    return ax
