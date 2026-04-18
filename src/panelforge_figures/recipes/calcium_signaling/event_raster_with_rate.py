"""Event raster with population-rate overlay — classic Ca²⁺ imaging summary."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class EventRasterInput(RecipeContract):
    t_bins: list[float] = Field(...)
    event_times: list[list[float]] = Field(
        ..., description="per-cell list of event times"
    )
    stim_times: list[float] = Field(default_factory=list)
    title: str = "Event raster · population rate"


def _demo() -> EventRasterInput:
    rng = np.random.default_rng(223)
    t_bins = np.linspace(0, 60, 200)
    n_cells = 40
    cells = []
    for _ in range(n_cells):
        # Spontaneous events + bursts around t=15 and t=40.
        n_spont = rng.poisson(4)
        spont = rng.uniform(0, 60, n_spont)
        burst1 = 15 + rng.normal(0, 1.0, rng.poisson(4))
        burst2 = 40 + rng.normal(0, 1.5, rng.poisson(6))
        events = np.concatenate([spont, burst1, burst2])
        events = events[(events > 0) & (events < 60)]
        cells.append(events.tolist())
    return EventRasterInput(
        t_bins=t_bins.tolist(),
        event_times=cells,
        stim_times=[15.0, 40.0],
    )


_META = RecipeMetadata(
    name="event_raster_with_rate",
    modality="calcium_signaling",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question="When does each cell fire, and what is the population mean rate over time?",
    required_fields=("t_bins", "event_times"),
    optional_fields=("stim_times", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("gcamp_trace_stack",),
)


@register_recipe(metadata=_META, contract=EventRasterInput, demo_contract=_demo)
def render(contract: EventRasterInput, ax=None, **_):
    """Host axis split into rate (top) + raster (bottom)."""
    import matplotlib.pyplot as plt
    if ax is None:
        fig = plt.figure(figsize=(5.4, 3.4))
        gs = fig.add_gridspec(2, 1, height_ratios=[1, 3], hspace=0.08)
        ax_rate = fig.add_subplot(gs[0, 0])
        ax_rast = fig.add_subplot(gs[1, 0], sharex=ax_rate)
    else:
        fig = ax.figure
        pos = ax.get_subplotspec()
        ax.remove()
        sub = pos.subgridspec(2, 1, height_ratios=[1, 3], hspace=0.08)
        ax_rate = fig.add_subplot(sub[0, 0])
        ax_rast = fig.add_subplot(sub[1, 0], sharex=ax_rate)

    AESTHETIC.apply_to_ax(ax_rate)
    AESTHETIC.apply_to_ax(ax_rast)
    palette = get_palette(AESTHETIC.primary_palette)
    accent = palette.pick("surveillant")

    t_bins = np.array(contract.t_bins, dtype=float)
    dt = t_bins[1] - t_bins[0] if t_bins.size >= 2 else 1.0

    # Build population rate (events per second per cell, averaged).
    rate = np.zeros_like(t_bins)
    for events in contract.event_times:
        for e in events:
            idx = int(np.searchsorted(t_bins, e))
            if 0 <= idx < t_bins.size:
                rate[idx] += 1
    rate = rate / max(dt, 1e-9) / max(len(contract.event_times), 1)

    # Smooth rate (rolling mean, window=5 bins).
    kernel = np.ones(5) / 5
    rate_smooth = np.convolve(rate, kernel, mode="same")

    ax_rate.fill_between(t_bins, 0, rate_smooth, color=accent, alpha=0.35,
                         linewidth=0, zorder=2)
    ax_rate.plot(t_bins, rate_smooth, color=accent, lw=1.2, zorder=3)
    ax_rate.set_ylabel("rate (Hz/cell)", fontsize=7.0)
    ax_rate.tick_params(labelbottom=False)
    ax_rate.set_title(contract.title, fontsize=9.0, pad=4)

    # Raster below.
    for i, events in enumerate(contract.event_times):
        if not events:
            continue
        ax_rast.scatter(events, [i] * len(events),
                        s=5, color="#111111", alpha=0.75, zorder=3,
                        marker="|")

    # Stim markers on both panels.
    for s in contract.stim_times:
        ax_rate.axvline(s, color="#D32F2F", lw=0.7, ls="--", zorder=4)
        ax_rast.axvline(s, color="#D32F2F", lw=0.7, ls="--", zorder=4)

    ax_rast.set_xlabel("time (s)")
    ax_rast.set_ylabel("cell id")
    ax_rast.set_xlim(t_bins[0], t_bins[-1])
    ax_rast.set_ylim(len(contract.event_times) - 0.5, -0.5)
    ax_rast.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax_rast.set_axisbelow(True)

    total_events = sum(len(e) for e in contract.event_times)
    ax_rate.text(0.99, 0.97,
                 f"N cells = {len(contract.event_times)}   "
                 f"total events = {total_events}\n"
                 f"peak rate = {smart_fmt(float(rate_smooth.max()))} Hz/cell",
                 transform=ax_rate.transAxes, ha="right", va="top",
                 fontsize=6.4, color="#333333",
                 bbox=dict(boxstyle="round,pad=0.18", fc="white",
                           ec="#BBBBBB", lw=0.5, alpha=0.92),
                 zorder=5)
    return ax_rate
