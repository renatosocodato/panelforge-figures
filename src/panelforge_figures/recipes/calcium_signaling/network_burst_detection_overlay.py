"""Detected network bursts overlaid on the event raster + rate.

Same raster + mean-rate grammar as `event_raster_with_rate`, with
explicit shaded burst epochs and start/end markers on both panels.
A burst-count / mean-duration callout summarises the detection.
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
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class NetworkBurstInput(RecipeContract):
    t_bins: list[float] = Field(...)
    event_times: list[list[float]] = Field(...)
    burst_start: list[float] = Field(..., description="burst onset times (s)")
    burst_end: list[float] = Field(..., description="burst offset times (s)")
    title: str = "Network-burst detection"


def _demo() -> NetworkBurstInput:
    rng = np.random.default_rng(257)
    t_bins = np.linspace(0, 60, 240)
    n_cells = 32
    cells = []
    burst_peaks = [12.0, 28.0, 45.0]
    for _ in range(n_cells):
        n_spont = rng.poisson(4)
        spont = rng.uniform(0, 60, n_spont)
        burst_events = np.concatenate([
            bp + rng.normal(0, 0.7, rng.poisson(7))
            for bp in burst_peaks
        ])
        events = np.concatenate([spont, burst_events])
        events = events[(events > 0) & (events < 60)]
        cells.append(np.sort(events).tolist())
    return NetworkBurstInput(
        t_bins=t_bins.tolist(),
        event_times=cells,
        burst_start=[10.5, 26.5, 43.5],
        burst_end=[13.5, 30.0, 47.0],
    )


_META = RecipeMetadata(
    name="network_burst_detection_overlay",
    modality="calcium_signaling",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question=(
        "Where along the recording do network bursts occur, overlaid "
        "on the raster + rate?"
    ),
    required_fields=("t_bins", "event_times", "burst_start", "burst_end"),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("event_raster_with_rate",),
)


@register_recipe(
    metadata=_META,
    contract=NetworkBurstInput,
    demo_contract=_demo,
)
def render(contract: NetworkBurstInput, ax=None, **_):
    import matplotlib.pyplot as plt
    if ax is None:
        fig = plt.figure(figsize=(5.8, 3.6))
        gs = fig.add_gridspec(2, 1, height_ratios=[1, 3], hspace=0.10)
        ax_rate = fig.add_subplot(gs[0, 0])
        ax_rast = fig.add_subplot(gs[1, 0], sharex=ax_rate)
    else:
        fig = ax.figure
        pos = ax.get_subplotspec()
        ax.remove()
        sub = pos.subgridspec(2, 1, height_ratios=[1, 3], hspace=0.10)
        ax_rate = fig.add_subplot(sub[0, 0])
        ax_rast = fig.add_subplot(sub[1, 0], sharex=ax_rate)

    AESTHETIC.apply_to_ax(ax_rate)
    AESTHETIC.apply_to_ax(ax_rast)
    palette = get_palette(AESTHETIC.primary_palette)
    accent = palette.pick("surveillant") if "surveillant" in palette.semantic else palette[0]
    burst_color = "#C62828"

    t_bins = np.asarray(contract.t_bins, float)
    dt = t_bins[1] - t_bins[0] if t_bins.size >= 2 else 1.0

    rate = np.zeros_like(t_bins)
    for events in contract.event_times:
        for e in events:
            idx = int(np.searchsorted(t_bins, e))
            if 0 <= idx < t_bins.size:
                rate[idx] += 1
    rate = rate / max(dt, 1e-9) / max(len(contract.event_times), 1)
    kernel = np.ones(5) / 5
    rate_smooth = np.convolve(rate, kernel, mode="same")

    ax_rate.fill_between(t_bins, 0, rate_smooth, color=accent, alpha=0.30,
                         linewidth=0, zorder=2)
    ax_rate.plot(t_bins, rate_smooth, color=accent, lw=1.2, zorder=3)
    ax_rate.set_ylabel("rate (Hz/cell)", fontsize=7.0)
    ax_rate.tick_params(labelbottom=False)

    # Raster.
    for i, events in enumerate(contract.event_times):
        if not events:
            continue
        ax_rast.scatter(events, [i] * len(events),
                        s=5, color="#111111", alpha=0.75, zorder=3,
                        marker="|")

    # Burst shading on both panels + onset / offset markers.
    burst_durations = []
    for i, (bs, be) in enumerate(zip(contract.burst_start, contract.burst_end)):
        for a in (ax_rate, ax_rast):
            a.axvspan(bs, be, color=burst_color, alpha=0.14, zorder=1)
        ax_rate.axvline(bs, color=burst_color, lw=0.7, ls="--", zorder=4)
        ax_rate.axvline(be, color=burst_color, lw=0.7, ls=":", zorder=4)
        ax_rate.text(0.5 * (bs + be), ax_rate.get_ylim()[1],
                     f"B{i+1}", ha="center", va="top", fontsize=6.2,
                     color=burst_color, zorder=5)
        burst_durations.append(be - bs)

    ax_rast.set_xlabel("time (s)")
    ax_rast.set_ylabel("cell id")
    ax_rast.set_xlim(t_bins[0], t_bins[-1])
    ax_rast.set_ylim(len(contract.event_times) - 0.5, -0.5)
    ax_rast.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax_rast.set_axisbelow(True)

    n_bursts = len(contract.burst_start)
    mean_dur = float(np.mean(burst_durations)) if burst_durations else 0.0
    # Fold the burst-count summary into the panel title so it never
    # overlaps any of the B-labels or the rate peaks.
    ax_rate.set_title(
        f"{contract.title}  ·  bursts = {n_bursts},  "
        f"mean dur = {smart_fmt(mean_dur)} s",
        fontsize=8.6, pad=4, color=burst_color,
    )
    return ax_rate
