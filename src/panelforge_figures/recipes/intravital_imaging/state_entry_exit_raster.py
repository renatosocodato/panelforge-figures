"""State entry/exit raster — per-cell rows × time columns coloured by
decoded state, with switch-tick markers at transitions.

Reveals heterogeneity that occupancy plots smooth over: which cells
spend most time in which state, when they switch, and whether the
switching pattern is bursty or steady. Cells sorted by total time
in the dominant state by default.

Matrix family: >=1 imshow OR >=4 cell patches. Satisfied by ≥4
state-segment Rectangle patches per cell (12 cells × ~5 segments
each = ~60 patches in the demo).
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
)
from ._aesthetic import AESTHETIC
from ._shared import DecodedStateSeries, _demo_state_palette


class StateEntryExitRasterInput(RecipeContract):
    decoded: list[DecodedStateSeries] = Field(..., min_length=3)
    states: list[str] = Field(..., min_length=2)
    sort_by: str = Field(
        "total_time_in_state",
        description="'total_time_in_state' | 'n_switches' | 'cell_id'",
    )
    sort_state: str | None = Field(
        None,
        description="state used for total_time_in_state sort; "
                    "defaults to the last in `states`",
    )
    decoder_label: str = "HMM"
    title: str = "State entry/exit raster"


def _demo() -> StateEntryExitRasterInput:
    rng = np.random.default_rng(2753)
    states = ["homeostatic", "surveillant", "activated"]
    n_t = 60
    n_cells = 12
    decoded = []
    for k in range(n_cells):
        # Sticky chain with cell-specific transition rates.
        switch_p = 0.05 + 0.10 * (k / n_cells)
        seq = []
        s = states[rng.integers(0, 3)]
        for _ in range(n_t):
            if rng.random() < switch_p:
                s = states[rng.integers(0, 3)]
            seq.append(s)
        decoded.append(DecodedStateSeries(
            cell_id=f"C{k:02d}",
            t_s=list(range(n_t)),
            state=seq,
            decoder="HMM",
        ))
    return StateEntryExitRasterInput(
        decoded=decoded,
        states=states,
    )


_META = RecipeMetadata(
    name="state_entry_exit_raster",
    modality="intravital_imaging",
    family=RecipeFamily.matrix,
    answers_question=(
        "Per cell, when do entries and exits between decoded states "
        "happen, and which cells dominate which state?"
    ),
    required_fields=("decoded", "states"),
    optional_fields=("sort_by", "sort_state", "decoder_label", "title"),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("posterior_state_probability_ribbons",),
)


@register_recipe(
    metadata=_META,
    contract=StateEntryExitRasterInput,
    demo_contract=_demo,
)
def render(contract: StateEntryExitRasterInput, ax=None, **_):
    import matplotlib.patches as mpatches
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 4.4))
    AESTHETIC.apply_to_ax(ax)

    palette = _demo_state_palette(contract.states)
    sort_state = contract.sort_state or contract.states[-1]

    def _sort_key(d: DecodedStateSeries) -> float:
        if contract.sort_by == "n_switches":
            return -sum(1 for prev, nxt in zip(d.state[:-1], d.state[1:])
                        if prev != nxt)
        if contract.sort_by == "cell_id":
            return float(hash(d.cell_id) % 10000)
        # default: total_time_in_state
        return -float(sum(1 for s in d.state if s == sort_state))

    cells = sorted(contract.decoded, key=_sort_key)

    # Per-cell row of state-segment rectangles.
    for yi, d in enumerate(cells):
        # Run-length encode the state sequence.
        i = 0
        while i < len(d.state):
            j = i
            while j < len(d.state) and d.state[j] == d.state[i]:
                j += 1
            colour = palette.get(d.state[i], "#888888")
            ax.add_patch(mpatches.Rectangle(
                (d.t_s[i] - 0.5, yi - 0.40),
                d.t_s[j-1] - d.t_s[i] + 1, 0.80,
                facecolor=colour, edgecolor="none",
                alpha=0.92, zorder=3,
            ))
            i = j
        # Switch ticks at transitions (drawn on top of the rectangles).
        for k in range(1, len(d.state)):
            if d.state[k] != d.state[k-1]:
                ax.plot([d.t_s[k] - 0.5, d.t_s[k] - 0.5],
                        [yi - 0.40, yi + 0.40],
                        color="#222222", lw=0.4, zorder=5)

    ax.set_yticks(range(len(cells)))
    ax.set_yticklabels([d.cell_id for d in cells], fontsize=6.6)
    ax.invert_yaxis()
    if cells:
        t_min = min(min(d.t_s) for d in cells)
        t_max = max(max(d.t_s) for d in cells)
        ax.set_xlim(t_min - 0.5, t_max + 0.5)
    ax.set_ylim(len(cells) - 0.5, -0.5)
    ax.set_xlabel("frame")
    ax.set_ylabel(f"cell  ·  sorted by {contract.sort_by}")

    # Legend.
    from matplotlib.patches import Patch
    handles = [Patch(facecolor=palette.get(s, "#888888"),
                     label=s, alpha=0.92)
               for s in contract.states]
    ax.legend(handles=handles, fontsize=6.4, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.10),
              ncols=len(contract.states), handlelength=1.0)

    # Per-cell n_switches summary in title.
    n_switches_total = 0
    for d in cells:
        for prev, nxt in zip(d.state[:-1], d.state[1:]):
            if prev != nxt:
                n_switches_total += 1
    n_cells_total = len(cells)
    ax.set_title(
        f"{contract.title}  ·  {contract.decoder_label}  ·  "
        f"{n_cells_total} cells  ·  {n_switches_total} switches",
        fontsize=8.2, pad=4,
    )
    return ax
