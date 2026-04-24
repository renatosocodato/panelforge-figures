"""Cell × time heatmap of ΔF/F aligned to stimulus onset.

Rows are cells (sorted by peak latency) and columns are time around
stimulus at t = 0. A mean ΔF/F trace is overlaid on top as an inset
strip. Distinct from `gcamp_trace_stack` (line traces) and
`spike_triggered_average` (one mean curve).
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


class StimTriggeredHeatmapInput(RecipeContract):
    time_s: list[float] = Field(..., min_length=3)
    cell_ids: list[str] = Field(..., min_length=2)
    dff_matrix: list[list[float]] = Field(
        ..., description="n_cells × n_time dF/F matrix aligned to stim at t=0"
    )
    sort_by_peak: bool = True
    title: str = "Stim-triggered Ca2+ heatmap"


def _demo() -> StimTriggeredHeatmapInput:
    rng = np.random.default_rng(523)
    t = np.linspace(-3.0, 10.0, 90)
    n = 40
    peaks = rng.uniform(0.3, 6.5, n)
    dff = np.zeros((n, t.size))
    for i, pk in enumerate(peaks):
        amp = rng.uniform(0.3, 1.0)
        dff[i] = amp * np.exp(-((t - pk) / 1.2) ** 2)
    # Baseline noise.
    dff += rng.normal(0, 0.06, dff.shape)
    # Half of the cells have almost no response.
    silent = rng.choice(n, size=n // 3, replace=False)
    dff[silent] = rng.normal(0, 0.04, (silent.size, t.size))
    return StimTriggeredHeatmapInput(
        time_s=t.tolist(),
        cell_ids=[f"c{i:03d}" for i in range(n)],
        dff_matrix=dff.tolist(),
    )


_META = RecipeMetadata(
    name="stimulus_triggered_calcium_heatmap",
    modality="calcium_signaling",
    family=RecipeFamily.heatmap,
    answers_question=(
        "Around a stimulus onset, how do all cells' ΔF/F traces align "
        "(cell × time heatmap)?"
    ),
    required_fields=("time_s", "cell_ids", "dff_matrix"),
    optional_fields=("sort_by_peak", "title"),
    file_format_hints=("csv", "parquet", "npz"),
    alternatives_in_modality=("gcamp_trace_stack", "spike_triggered_average"),
)


@register_recipe(
    metadata=_META,
    contract=StimTriggeredHeatmapInput,
    demo_contract=_demo,
)
def render(contract: StimTriggeredHeatmapInput, ax=None, **_):
    import matplotlib as mpl
    import matplotlib.pyplot as plt

    if ax is None:
        fig = plt.figure(figsize=(5.6, 4.0))
        gs = fig.add_gridspec(2, 1, height_ratios=[1, 4], hspace=0.06)
        ax_mean = fig.add_subplot(gs[0, 0])
        ax_hm = fig.add_subplot(gs[1, 0], sharex=ax_mean)
    else:
        fig = ax.figure
        pos = ax.get_subplotspec()
        ax.remove()
        sub = pos.subgridspec(2, 1, height_ratios=[1, 4], hspace=0.06)
        ax_mean = fig.add_subplot(sub[0, 0])
        ax_hm = fig.add_subplot(sub[1, 0], sharex=ax_mean)

    for a in (ax_mean, ax_hm):
        AESTHETIC.apply_to_ax(a)

    t = np.asarray(contract.time_s, float)
    M = np.asarray(contract.dff_matrix, float)
    cell_ids = list(contract.cell_ids)
    if contract.sort_by_peak:
        # Sort cells by time of peak.
        peak_t = t[np.argmax(M, axis=1)]
        order = np.argsort(peak_t)
        M = M[order]
        cell_ids = [cell_ids[i] for i in order]

    cmap = mpl.colormaps[AESTHETIC.continuous_cmap]
    vmax = float(np.quantile(np.abs(M), 0.98))
    im = ax_hm.imshow(
        M, cmap=cmap,
        extent=(t[0], t[-1], M.shape[0] - 0.5, -0.5),
        aspect="auto", interpolation="nearest",
        vmin=-vmax, vmax=vmax,
    )

    # Stim line at t = 0.
    for a in (ax_mean, ax_hm):
        a.axvline(0, color="#D32F2F", lw=0.8, ls="--", zorder=4)

    # Mean trace on top.
    mean_trace = np.mean(M, axis=0)
    sem_trace = np.std(M, axis=0) / np.sqrt(max(M.shape[0], 1))
    ax_mean.fill_between(t, mean_trace - sem_trace, mean_trace + sem_trace,
                         color="#43A047", alpha=0.30, linewidth=0, zorder=2)
    ax_mean.plot(t, mean_trace, color="#2E7D32", lw=1.3, zorder=3)
    ax_mean.tick_params(labelbottom=False, labelsize=6.4)
    ax_mean.set_ylabel(r"mean $\Delta F/F$", fontsize=7.0)
    ax_mean.set_title(contract.title, fontsize=9.0, pad=4)
    ax_mean.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax_mean.set_axisbelow(True)

    ax_hm.set_xlabel("time from stim (s)")
    ax_hm.set_ylabel("cell (sorted by peak)")
    ax_hm.set_yticks([0, M.shape[0] // 2, M.shape[0] - 1])
    ax_hm.set_yticklabels([cell_ids[0],
                           cell_ids[M.shape[0] // 2],
                           cell_ids[-1]], fontsize=6.0)
    ax_hm.set_xlim(t[0], t[-1])

    cbar = ax_hm.figure.colorbar(im, ax=ax_hm, fraction=0.040, pad=0.03)
    cbar.set_label(r"$\Delta F/F$", fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    # Peak stats callout.
    pk_t = float(t[int(np.argmax(mean_trace))])
    pk_val = float(mean_trace.max())
    ax_mean.text(
        0.99, 0.97,
        f"peak {smart_fmt(pk_val)} at t={smart_fmt(pk_t)} s",
        transform=ax_mean.transAxes, ha="right", va="top",
        fontsize=6.4, color="#111111",
        bbox=dict(boxstyle="round,pad=0.18", fc="white",
                  ec="#BBBBBB", lw=0.5, alpha=0.92),
        zorder=6,
    )
    return ax_mean
