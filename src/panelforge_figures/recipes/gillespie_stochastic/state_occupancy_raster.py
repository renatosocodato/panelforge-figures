"""State occupancy raster — N trials × time with state-shaded segments."""

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


class StateRasterInput(RecipeContract):
    t: list[float] = Field(...)
    state_sequences: list[list[int]] = Field(
        ..., description="for each trial, state id at each time point"
    )
    state_names: list[str] = Field(..., description="names indexed by state id")
    title: str = "State occupancy raster"


def _demo() -> StateRasterInput:
    rng = np.random.default_rng(127)
    t = np.linspace(0, 30, 300)
    n_trials = 40
    seqs = []
    # Each trial: random HOME→GATE→TRAP sequence with exponential dwells.
    state_names = ["HOME", "GATE", "TRAP"]
    for _ in range(n_trials):
        seq = np.zeros(t.size, dtype=int)
        cur = 0
        t_now = 0.0
        while t_now < t[-1]:
            dwell = rng.exponential(5.0)
            idx_lo = int(np.searchsorted(t, t_now))
            t_now += dwell
            idx_hi = int(np.searchsorted(t, t_now))
            seq[idx_lo:idx_hi] = cur
            cur = min(cur + 1, 2) if rng.random() > 0.25 else max(cur - 1, 0)
        seqs.append(seq.tolist())
    return StateRasterInput(
        t=t.tolist(),
        state_sequences=seqs,
        state_names=state_names,
    )


_META = RecipeMetadata(
    name="state_occupancy_raster",
    modality="gillespie_stochastic",
    family=RecipeFamily.heatmap,
    answers_question="Per trial, which state is occupied at each time, aligned across many trials?",
    required_fields=("t", "state_sequences", "state_names"),
    optional_fields=("title",),
    file_format_hints=("parquet", "pickle"),
    alternatives_in_modality=("trajectory_fan_with_fpt",),
)


@register_recipe(metadata=_META, contract=StateRasterInput, demo_contract=_demo)
def render(contract: StateRasterInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    t = np.array(contract.t, dtype=float)
    M = np.array(contract.state_sequences, dtype=int)
    n_trials = M.shape[0]
    state_names = contract.state_names

    # Map state ids → palette semantic colors when possible.
    name_color = {
        "HOME": palette.pick("HOME"),
        "GATE": palette.pick("GATE"),
        "TRAP": palette.pick("TRAP"),
    }
    colors = [
        name_color.get(nm, palette[i])
        for i, nm in enumerate(state_names)
    ]

    from matplotlib.colors import ListedColormap
    cmap = ListedColormap(colors)

    ax.imshow(M, aspect="auto", cmap=cmap,
              extent=(t[0], t[-1], n_trials, 0),
              interpolation="nearest")
    ax.set_xlabel("time")
    ax.set_ylabel("trial")
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    # Legend via matplotlib Patch proxies.
    from matplotlib.patches import Patch
    proxies = [
        Patch(facecolor=colors[i], edgecolor="none", label=nm)
        for i, nm in enumerate(state_names)
    ]
    ax.legend(handles=proxies, loc="upper right", bbox_to_anchor=(1.0, 1.18),
              ncol=len(state_names), fontsize=6.8, frameon=False,
              handlelength=1.0, columnspacing=1.0)

    # State-occupancy summary (% of time per state, pooled over trials).
    fractions = [(M == i).mean() for i in range(len(state_names))]
    summary = "   ".join(
        f"{nm}: {100 * f:.0f}%"
        for nm, f in zip(state_names, fractions)
    )
    ax.text(0.01, -0.16, summary,
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.6, color="#333333",
            bbox=dict(boxstyle="round,pad=0.20", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=5)
    return ax
