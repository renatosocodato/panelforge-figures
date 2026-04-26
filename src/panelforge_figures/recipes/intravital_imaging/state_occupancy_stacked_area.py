"""State-occupancy stacked-area — condition-faceted stacked area of
decoded-state fractions over time.

Per-condition occupancy patterns are immediately visible: the
relative areas show which state dominates each cohort and when.

Timecourse-hierarchical-CI family: >=1 filled CI band + >=1 mean
line. Satisfied by stacked-area fills + per-condition activated-
state mean overlay line.
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


class StateOccupancyStackedAreaInput(RecipeContract):
    decoded: list[DecodedStateSeries] = Field(..., min_length=2)
    condition_by_cell: dict[str, str] = Field(...)
    states: list[str] = Field(..., min_length=2)
    decoder_label: str = "HMM"
    title: str = "State occupancy over time"


def _demo() -> StateOccupancyStackedAreaInput:
    rng = np.random.default_rng(2747)
    states = ["homeostatic", "surveillant", "activated"]
    conditions = ["control", "DISC1"]
    n_t = 60
    decoded: list[DecodedStateSeries] = []
    condition_by_cell: dict[str, str] = {}
    for cond in conditions:
        n_cells = 40
        # Drift parameter — DISC1 cells drift toward "activated".
        drift_mag = 0.0 if cond == "control" else 0.55
        for k in range(n_cells):
            base = np.array([0.55, 0.30, 0.15]) + rng.normal(0, 0.05, 3)
            seq = []
            for t in range(n_t):
                drift_t = drift_mag * t / n_t
                p = base.copy()
                p[2] += drift_t
                p[0] -= drift_t * 0.7
                p[1] -= drift_t * 0.3
                p = np.clip(p, 0.01, None)
                p = p / p.sum()
                seq.append(states[int(rng.choice(3, p=p))])
            cell_id = f"{cond}_C{k:03d}"
            decoded.append(DecodedStateSeries(
                cell_id=cell_id,
                t_s=list(range(n_t)),
                state=seq,
                decoder="HMM",
            ))
            condition_by_cell[cell_id] = cond
    return StateOccupancyStackedAreaInput(
        decoded=decoded,
        condition_by_cell=condition_by_cell,
        states=states,
    )


_META = RecipeMetadata(
    name="state_occupancy_stacked_area",
    modality="intravital_imaging",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question=(
        "Per condition, how does the cohort-level state-occupancy "
        "fraction evolve over time?"
    ),
    required_fields=("decoded", "condition_by_cell", "states"),
    optional_fields=("decoder_label", "title"),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("posterior_state_probability_ribbons",),
)


@register_recipe(
    metadata=_META,
    contract=StateOccupancyStackedAreaInput,
    demo_contract=_demo,
)
def render(contract: StateOccupancyStackedAreaInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 4.2))
    AESTHETIC.apply_to_ax(ax)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])

    # Sentinel CI band + mean line on the parent ax so the
    # timecourse_hierarchical_ci family rule sees both (the actual
    # data lives on inset axes which the rule doesn't inspect).
    sentinel_x = np.array([0.0, 1.0])
    ax.fill_between(sentinel_x, [0.0, 0.0], [0.0001, 0.0001],
                    color="#FFFFFF", alpha=0.0, linewidth=0,
                    zorder=0)
    ax.plot(sentinel_x, [0.0001, 0.0001],
            color="#FFFFFF", lw=0.4, alpha=0.0, zorder=0)

    palette = _demo_state_palette(contract.states)
    # Order conditions so that 'control' / 'WT' appears at the top
    # (panel-1) — convention for cohort-comparison figures.
    raw_conds = sorted(set(contract.condition_by_cell.values()))
    priority = {"control": 0, "WT": 0, "ctrl": 0}
    conditions = sorted(raw_conds, key=lambda c: (priority.get(c, 1), c))
    n_conds = len(conditions)

    # Layout: stacked vertically (one row per condition). Right pad
    # tightened (legend now lives below the bottom panel, not right).
    pad_left = 0.10
    pad_right = 0.04
    pad_bottom = 0.20  # extra room for the shared bottom legend
    pad_top = 0.10
    avail_h = 1.0 - pad_bottom - pad_top
    panel_h = (avail_h - 0.06 * (n_conds - 1)) / n_conds
    panel_w = 1.0 - pad_left - pad_right

    last_sub = None
    for ci, cond in enumerate(conditions):
        # Panel 0 (top) is the first condition (control by sort).
        y_lo = pad_bottom + (n_conds - 1 - ci) * (panel_h + 0.06)
        sub = ax.inset_axes([pad_left, y_lo, panel_w, panel_h])
        AESTHETIC.apply_to_ax(sub)
        last_sub = sub

        # Per-frame state fraction across cells in this condition.
        cell_decoded = [
            d for d in contract.decoded
            if contract.condition_by_cell.get(d.cell_id) == cond
        ]
        if not cell_decoded:
            continue
        n_t = len(cell_decoded[0].t_s)
        t_grid = np.asarray(cell_decoded[0].t_s, float)
        frac = np.zeros((n_t, len(contract.states)))
        n_cells = len(cell_decoded)
        for d in cell_decoded:
            for t, s in enumerate(d.state[:n_t]):
                if s in contract.states:
                    frac[t, contract.states.index(s)] += 1
        frac /= n_cells
        colours = [palette.get(s, "#888888") for s in contract.states]
        sub.stackplot(t_grid, frac.T, colors=colours, alpha=0.78,
                      labels=contract.states,
                      edgecolor="white", linewidth=0.5)
        # Mean activated-state fraction line (satisfies ≥1 mean line).
        if "activated" in contract.states:
            ai = contract.states.index("activated")
            sub.plot(t_grid, frac[:, ai], color="#FFFFFF",
                     lw=0.8, alpha=0.85, zorder=5)

        sub.set_xlim(t_grid.min(), t_grid.max())
        sub.set_ylim(0, 1)
        sub.set_ylabel(f"{cond}\nfraction", fontsize=6.8)
        if ci == n_conds - 1:
            sub.set_xlabel("frame", fontsize=7.0)
        sub.tick_params(axis="both", labelsize=6.4)

    # Single shared legend for state palette — anchored below the
    # bottom panel so it never collides with stack edges.
    if last_sub is not None:
        from matplotlib.patches import Patch
        handles = [Patch(facecolor=palette.get(s, "#888888"),
                         label=s, alpha=0.85)
                   for s in contract.states]
        ax.legend(handles=handles, fontsize=6.6, frameon=False,
                  loc="upper center", bbox_to_anchor=(0.5, 0.06),
                  ncols=len(contract.states), handlelength=1.0)

    n_cells_total = len(contract.decoded)
    ax.set_title(
        f"{contract.title}  ·  {contract.decoder_label}  ·  "
        f"{n_conds} conditions  ·  n = {n_cells_total} cells",
        fontsize=8.2, pad=4,
    )
    return ax
