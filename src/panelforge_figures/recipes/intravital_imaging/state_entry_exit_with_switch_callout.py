"""State entry/exit raster with switch-rate callout — variant of
`state_entry_exit_raster` that adds a left-margin lollipop-style
per-cell switch-rate annotation, plus a per-row callout colour
(amber if switch rate > 75th percentile across cells).

The recipe consumes the same `DecodedStateSeries` atom as the base
recipe but bundles each cell with a precomputed `StateSwitchSummary`
so the callout doesn't recount transitions on every render.

Matrix family: >=1 imshow OR >=4 cell patches. Satisfied by the
state-segment Rectangles (12 cells × ~5 segments each = ~60 patches
in the demo).
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
from ._shared import (
    DecodedStateSeries,
    StateSwitchSummary,
    _demo_state_palette,
)


class StateEntryExitWithSwitchCalloutInput(RecipeContract):
    decoded: list[DecodedStateSeries] = Field(..., min_length=3)
    switches: list[StateSwitchSummary] = Field(..., min_length=3)
    states: list[str] = Field(..., min_length=2)
    decoder_label: str = "HMM"
    title: str = "State entry/exit raster with switch-rate callout"


def _demo() -> StateEntryExitWithSwitchCalloutInput:
    rng = np.random.default_rng(826)
    states = ["homeostatic", "surveillant", "activated"]
    n_t = 60
    n_cells = 12
    decoded: list[DecodedStateSeries] = []
    switches: list[StateSwitchSummary] = []
    for k in range(n_cells):
        # Sticky chain with cell-specific switch probability.
        switch_p = 0.05 + 0.10 * (k / n_cells)
        seq: list[str] = []
        s = states[rng.integers(0, 3)]
        for _ in range(n_t):
            if rng.random() < switch_p:
                s = states[rng.integers(0, 3)]
            seq.append(s)
        n_sw = sum(1 for prev, nxt in zip(seq[:-1], seq[1:])
                   if prev != nxt)
        # 60 frames × 1 s = 60 s = 1 min total per cell.
        duration_min = float(n_t) / 60.0
        decoded.append(DecodedStateSeries(
            cell_id=f"C{k:02d}",
            t_s=list(range(n_t)),
            state=seq,
            decoder="HMM",
        ))
        switches.append(StateSwitchSummary(
            cell_id=f"C{k:02d}",
            n_switches=n_sw,
            duration_min=duration_min,
            switch_rate_per_min=n_sw / duration_min,
        ))
    return StateEntryExitWithSwitchCalloutInput(
        decoded=decoded,
        switches=switches,
        states=states,
    )


_META = RecipeMetadata(
    name="state_entry_exit_with_switch_callout",
    modality="intravital_imaging",
    family=RecipeFamily.matrix,
    answers_question=(
        "Per cell, when do entries and exits between decoded states "
        "happen, and which cells stand out as high-switch-rate "
        "outliers above the 75th percentile?"
    ),
    required_fields=("decoded", "switches", "states"),
    optional_fields=("decoder_label", "title"),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("state_entry_exit_raster",),
)


@register_recipe(
    metadata=_META,
    contract=StateEntryExitWithSwitchCalloutInput,
    demo_contract=_demo,
)
def render(
    contract: StateEntryExitWithSwitchCalloutInput, ax=None, **_,
):
    import matplotlib.patches as mpatches
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(7.0, 4.4))
    AESTHETIC.apply_to_ax(ax)

    palette = _demo_state_palette(contract.states)
    sw_by_id = {s.cell_id: s for s in contract.switches}

    # Sort cells by switch-rate (descending) so the high-switchers sit at top.
    cells = sorted(
        contract.decoded,
        key=lambda d: -sw_by_id.get(
            d.cell_id, StateSwitchSummary(
                cell_id=d.cell_id, n_switches=0,
                duration_min=1.0, switch_rate_per_min=0.0,
            ),
        ).switch_rate_per_min,
    )

    # 75th-percentile threshold for the amber callout colour.
    rates = np.array(
        [sw_by_id[d.cell_id].switch_rate_per_min for d in cells],
        float,
    )
    q75 = float(np.quantile(rates, 0.75)) if rates.size else 0.0

    # Reserve a left-margin band for the switch-rate callout. The state
    # raster lives at frame >= 0; the callout lives at frame in [-x_pad, -1].
    if cells:
        t_min = min(min(d.t_s) for d in cells)
        t_max = max(max(d.t_s) for d in cells)
    else:
        t_min, t_max = 0, 1
    span = max(t_max - t_min, 1)
    x_pad = max(span * 0.18, 8.0)

    # Per-cell row of state-segment rectangles.
    for yi, d in enumerate(cells):
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
        # Switch ticks at transitions.
        for k in range(1, len(d.state)):
            if d.state[k] != d.state[k-1]:
                ax.plot([d.t_s[k] - 0.5, d.t_s[k] - 0.5],
                        [yi - 0.40, yi + 0.40],
                        color="#222222", lw=0.4, zorder=5)

        # --- Switch-rate callout ----------------------------------
        sw = sw_by_id[d.cell_id]
        # Callout colour: amber if above 75th percentile, slate otherwise.
        cb_colour = "#FFB300" if sw.switch_rate_per_min >= q75 else "#90A4AE"
        # Lollipop stem from x = -x_pad to x = -1; length proportional
        # to switch-rate fraction of max.
        rate_max = max(rates.max() if rates.size else 1.0, 1e-3)
        frac = sw.switch_rate_per_min / rate_max
        x_lo = t_min - x_pad
        x_hi = t_min - 2.0
        x_marker = x_lo + frac * (x_hi - x_lo)
        ax.plot([x_lo, x_marker], [yi, yi], color=cb_colour,
                lw=1.4, zorder=4)
        ax.scatter([x_marker], [yi], s=24, marker="o",
                   facecolor=cb_colour, edgecolor="white",
                   linewidth=0.5, zorder=5)
        # Inline rate annotation positioned just above the lollipop
        # stem so it does not collide with cell-id y-tick labels in
        # the leftmost margin.
        ax.text(x_lo + (x_marker - x_lo) / 2, yi - 0.30,
                f"{smart_fmt(sw.switch_rate_per_min)}/min",
                ha="center", va="bottom", fontsize=5.6,
                color=cb_colour, fontweight="bold", zorder=6)

    ax.set_yticks(range(len(cells)))
    ax.set_yticklabels([d.cell_id for d in cells], fontsize=6.6)
    ax.invert_yaxis()
    ax.set_xlim(t_min - x_pad - 8.0, t_max + 0.5)
    ax.set_ylim(len(cells) - 0.5, -0.5)
    ax.set_xlabel("frame  ·  switch-rate callout in left margin")
    ax.set_ylabel("cell  ·  sorted by switch-rate")

    # Vertical separator between callout and raster.
    ax.axvline(t_min - 1.0, color="#BDBDBD", lw=0.5, ls=":", zorder=2)

    # Legend: state colours + callout-percentile semantics.
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    handles = [Patch(facecolor=palette.get(s, "#888888"),
                     label=s, alpha=0.92)
               for s in contract.states]
    handles += [
        Line2D([0], [0], marker="o", color="#FFB300", lw=1.4,
               markerfacecolor="#FFB300", markeredgecolor="white",
               markersize=6, label="switch-rate ≥ Q75"),
        Line2D([0], [0], marker="o", color="#90A4AE", lw=1.4,
               markerfacecolor="#90A4AE", markeredgecolor="white",
               markersize=6, label="switch-rate < Q75"),
    ]
    ax.legend(handles=handles, fontsize=6.4, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.10),
              ncols=len(contract.states) + 2, handlelength=1.0)

    n_high = int(np.sum(rates >= q75)) if rates.size else 0
    ax.set_title(
        f"{contract.title}  ·  {contract.decoder_label}  ·  "
        f"{n_high}/{len(cells)} cells ≥ Q75  ·  Q75 = "
        f"{smart_fmt(q75)} switches/min",
        fontsize=8.2, pad=4,
    )
    return ax
