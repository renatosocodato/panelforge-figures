"""Protrusion dominance race - per-cell delta-L(t) traces colored by
winner/runner-up + winning-margin distribution callout.

Scatter-collapse family: >=1 scatter + >=1 fit line.
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

_WINNER_COLOR = "#26A69A"   # teal
_RUNNERUP_COLOR = "#EF5350"  # coral


class DominanceRaceCell(RecipeContract):
    cell_id: str
    t_s: list[float]
    delta_L_winner_um: list[float]
    delta_L_runnerup_um: list[float]


class ProtrusionDominanceRaceInput(RecipeContract):
    cells: list[DominanceRaceCell] = Field(..., min_length=3)
    title: str = "Protrusion dominance race"


def _demo() -> ProtrusionDominanceRaceInput:
    rng = np.random.default_rng(3071)
    cells: list[DominanceRaceCell] = []
    n_t = 60
    t = np.arange(n_t).astype(float)
    for k in range(12):
        # Winner grows ~8 um by end; runner-up retracts to ~-2 um.
        win = np.cumsum(rng.normal(0.18, 0.20, n_t))
        run = np.cumsum(rng.normal(-0.04, 0.14, n_t))
        cells.append(DominanceRaceCell(
            cell_id=f"C{k:02d}",
            t_s=t.tolist(),
            delta_L_winner_um=win.tolist(),
            delta_L_runnerup_um=run.tolist(),
        ))
    return ProtrusionDominanceRaceInput(cells=cells)


_META = RecipeMetadata(
    name="protrusion_dominance_race_winner",
    modality="intravital_imaging",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "When two protrusions emerge concurrently, what is the "
        "winner-vs-runner-up dynamic and the winning margin?"
    ),
    required_fields=("cells",),
    optional_fields=("title",),
    file_format_hints=("yaml",),
    alternatives_in_modality=("protrusion_commitment_survival",),
)


@register_recipe(
    metadata=_META,
    contract=ProtrusionDominanceRaceInput,
    demo_contract=_demo,
)
def render(contract: ProtrusionDominanceRaceInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.8, 3.8))
    AESTHETIC.apply_to_ax(ax)

    # Per-cell scatter at endpoints + traces.
    end_winners = []
    end_runners = []
    for cell in contract.cells:
        t = np.asarray(cell.t_s, float)
        win = np.asarray(cell.delta_L_winner_um, float)
        run = np.asarray(cell.delta_L_runnerup_um, float)
        ax.plot(t, win, color=_WINNER_COLOR, lw=0.9, alpha=0.55,
                zorder=4)
        ax.plot(t, run, color=_RUNNERUP_COLOR, lw=0.9, alpha=0.55,
                zorder=4)
        end_winners.append(float(win[-1]))
        end_runners.append(float(run[-1]))

    # Mean traces (the ≥1 fit line for scatter_collapse).
    if contract.cells:
        n_t = len(contract.cells[0].t_s)
        all_win = np.array([c.delta_L_winner_um[:n_t]
                            for c in contract.cells])
        all_run = np.array([c.delta_L_runnerup_um[:n_t]
                            for c in contract.cells])
        t = np.asarray(contract.cells[0].t_s, float)[:n_t]
        ax.plot(t, all_win.mean(axis=0), color=_WINNER_COLOR, lw=1.4,
                zorder=6, label="winner (mean)")
        ax.plot(t, all_run.mean(axis=0), color=_RUNNERUP_COLOR, lw=1.4,
                zorder=6, label="runner-up (mean)")

    # Endpoint scatter.
    end_t = float(t[-1]) if contract.cells else 1.0
    ax.scatter([end_t] * len(end_winners), end_winners,
               s=22, color=_WINNER_COLOR, edgecolor="white",
               linewidth=0.4, zorder=7)
    ax.scatter([end_t] * len(end_runners), end_runners,
               s=22, color=_RUNNERUP_COLOR, edgecolor="white",
               linewidth=0.4, zorder=7)

    ax.axhline(0, color="#DDDDDD", lw=0.4, zorder=1)
    ax.set_xlabel("time (s)")
    ax.set_ylabel("delta L (um)")
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.8, frameon=False, loc="upper left",
              handlelength=1.4)

    margin = float(np.median(np.array(end_winners) - np.array(end_runners)))
    ax.set_title(
        f"{contract.title}  ·  n = {len(contract.cells)} cells  ·  "
        f"median winning margin = {smart_fmt(margin)} um",
        fontsize=8.4, pad=4,
    )
    return ax
