"""Per-cell event raster — discrete events over time, rows = cells.

Each row is one cell, each glyph on the row marks a discrete event
(extension, retraction, contact, lysis…). Row background shades the
cell's dominant state over the window. Columns summarise total events
per time bin at the bottom.
"""

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


class CellEventRow(RecipeContract):
    cell_id: str
    dominant_state: str
    event_times: dict[str, list[float]] = Field(
        ..., description="event_type → list of times (min)"
    )


class EventTimelineInput(RecipeContract):
    cells: list[CellEventRow] = Field(..., min_length=3)
    window_min: float = 60.0
    event_type_order: list[str] | None = None
    title: str = "Per-cell event timeline"


def _demo() -> EventTimelineInput:
    rng = np.random.default_rng(617)
    states = ["homeostatic", "surveillant", "activated"]
    events = ["extension", "retraction", "contact"]
    cells = []
    for i in range(14):
        state = rng.choice(states, p=[0.45, 0.35, 0.20])
        rates = {
            "homeostatic": {"extension": 4, "retraction": 3, "contact": 1},
            "surveillant": {"extension": 9, "retraction": 7, "contact": 4},
            "activated":   {"extension": 6, "retraction": 5, "contact": 11},
        }[state]
        et = {
            ev: sorted(rng.uniform(0, 60, int(rng.poisson(rates[ev]))).tolist())
            for ev in events
        }
        cells.append(CellEventRow(
            cell_id=f"c{i:02d}", dominant_state=state, event_times=et,
        ))
    return EventTimelineInput(
        cells=cells,
        window_min=60.0,
        event_type_order=events,
    )


_META = RecipeMetadata(
    name="process_event_timeline",
    modality="intravital_imaging",
    family=RecipeFamily.matrix,
    answers_question=(
        "Per cell, when do discrete events (extension, retraction, "
        "contact, lysis) occur across the observation window?"
    ),
    required_fields=("cells",),
    optional_fields=("window_min", "event_type_order", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("cell_track_trajectory_field",),
)


@register_recipe(
    metadata=_META,
    contract=EventTimelineInput,
    demo_contract=_demo,
)
def render(contract: EventTimelineInput, ax=None, **_):
    import matplotlib.patches as mpatches

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.0, 4.0))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    cells = contract.cells
    n = len(cells)
    events = (contract.event_type_order
              or sorted({e for c in cells for e in c.event_times}))
    # Marker styles per event type.
    markers = {
        events[i]: ("o", "s", "^", "D", "v", "P", "*")[i % 7]
        for i in range(len(events))
    }
    # Colors per event type from a neutral palette of Okabe-Ito.
    ev_colors = ["#1565C0", "#EF6C00", "#2E7D32", "#6A1B9A", "#AD1457"]

    # Row background shades by dominant state.
    y = np.arange(n)[::-1]
    for yi, cell in zip(y, cells):
        state_c = (palette.pick(cell.dominant_state)
                   if cell.dominant_state in palette.semantic
                   else palette[0])
        ax.add_patch(mpatches.Rectangle(
            (0, yi - 0.40), contract.window_min, 0.80,
            facecolor=state_c, edgecolor="none", alpha=0.10,
            zorder=1,
        ))

    # Event glyphs.
    for yi, cell in zip(y, cells):
        for ei, ev_type in enumerate(events):
            times = cell.event_times.get(ev_type, [])
            if not times:
                continue
            t = np.asarray(times, float)
            ax.scatter(
                t, np.full_like(t, yi), s=22,
                marker=markers[ev_type],
                color=ev_colors[ei % len(ev_colors)],
                edgecolor="white", linewidth=0.3, zorder=3,
                alpha=0.9,
            )

    # Bottom per-bin event totals bar.
    total_events = np.zeros(60)
    bin_edges = np.linspace(0, contract.window_min, 61)
    for cell in cells:
        for times in cell.event_times.values():
            h, _ = np.histogram(times, bins=bin_edges)
            total_events = total_events + h
    scale = 0.9 / max(total_events.max(), 1)
    for bi, count in enumerate(total_events):
        ax.add_patch(mpatches.Rectangle(
            (bin_edges[bi], -1.6 - 0.35),
            bin_edges[bi + 1] - bin_edges[bi],
            scale * count,
            facecolor="#666666", edgecolor="none", zorder=2,
        ))
    ax.text(contract.window_min, -1.6 + 0.10,
            " total events / min",
            ha="left", va="bottom", fontsize=6.2, color="#666666")

    ax.set_xlim(0, contract.window_min)
    ax.set_ylim(-2.4, n - 0.2)
    ax.set_yticks(y)
    ax.set_yticklabels([c.cell_id for c in cells], fontsize=6.6)
    ax.set_xlabel("time (min)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    # Legend proxies.
    from matplotlib.lines import Line2D
    ev_proxies = [
        Line2D([0], [0], linestyle="", marker=markers[ev],
               markerfacecolor=ev_colors[i % len(ev_colors)],
               markeredgecolor="white", markersize=6, label=ev)
        for i, ev in enumerate(events)
    ]
    state_proxies = [
        mpatches.Patch(facecolor=palette.pick(s), alpha=0.25, label=s)
        for s in ("homeostatic", "surveillant", "activated")
        if s in palette.semantic
    ]
    ax.legend(
        handles=ev_proxies + state_proxies,
        fontsize=6.4, frameon=False, loc="center left",
        bbox_to_anchor=(1.02, 0.5), handlelength=1.4,
    )
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
