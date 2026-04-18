"""Spike-triggered average — average ΔF/F aligned to each event with CI ribbon."""

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


class STAInput(RecipeContract):
    t_window: list[float] = Field(..., description="time window around spike (s)")
    aligned_traces: list[list[float]] = Field(
        ..., description="per-spike snippets aligned to spike time t=0"
    )
    signal_name: str = r"$\Delta$F/F"
    title: str = "Spike-triggered average"


def _demo() -> STAInput:
    rng = np.random.default_rng(239)
    t = np.linspace(-1.0, 2.5, 140)
    n_spikes = 80
    snippets = []
    # Each snippet: transient rise at t=0, exponential decay.
    for _ in range(n_spikes):
        amp = rng.uniform(0.5, 1.6)
        tau = rng.uniform(0.4, 1.0)
        trace = np.where(t >= 0, amp * np.exp(-t / tau), 0.0) \
                + rng.normal(0, 0.06, t.size)
        snippets.append(trace.tolist())
    return STAInput(
        t_window=t.tolist(),
        aligned_traces=snippets,
    )


_META = RecipeMetadata(
    name="spike_triggered_average",
    modality="calcium_signaling",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question="What is the average calcium-transient waveform aligned to each detected spike?",
    required_fields=("t_window", "aligned_traces"),
    optional_fields=("signal_name", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("gcamp_trace_stack",),
)


@register_recipe(metadata=_META, contract=STAInput, demo_contract=_demo)
def render(contract: STAInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)
    accent = palette.pick("activated")

    t = np.array(contract.t_window, dtype=float)
    snips = np.vstack([np.array(s, float) for s in contract.aligned_traces])

    mean = snips.mean(axis=0)
    sem = snips.std(axis=0) / np.sqrt(snips.shape[0])

    ax.fill_between(t, mean - 1.96 * sem, mean + 1.96 * sem,
                    color=accent, alpha=0.22, linewidth=0, zorder=2,
                    label="95% CI")
    ax.plot(t, mean, color=accent, lw=1.3, zorder=3, label="mean")

    # Baseline zero line.
    ax.axhline(0, color="#888888", lw=0.5, ls=":", zorder=1)
    # Spike marker.
    ax.axvline(0, color="#D32F2F", lw=0.7, ls="--", zorder=4)

    # Peak annotation.
    i_peak = int(np.argmax(mean))
    ax.scatter([t[i_peak]], [mean[i_peak]], s=32, marker="*",
               color="#D32F2F", edgecolor="white", linewidth=0.8,
               zorder=5)
    ax.text(t[i_peak], mean[i_peak] * 1.04,
            f"peak = {smart_fmt(float(mean[i_peak]))}",
            ha="center", va="bottom", fontsize=6.6, color="#D32F2F",
            bbox=dict(boxstyle="round,pad=0.16", fc="white",
                      ec="none", alpha=0.92),
            zorder=6)

    ax.set_xlabel("time from spike (s)")
    ax.set_ylabel(contract.signal_name)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              handlelength=1.8)

    ax.text(0.01, 0.99,
            f"N spikes = {snips.shape[0]}",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.4, color="#444444",
            bbox=dict(boxstyle="round,pad=0.18", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=7)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
