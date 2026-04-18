"""Stimulus-response fan — per-cell traces aligned to stim + mean overlay."""

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


class StimulusFanInput(RecipeContract):
    t: list[float] = Field(..., description="time aligned so stim is at t=0")
    traces: list[list[float]] = Field(
        ..., description="per-cell traces aligned to t"
    )
    stim_duration_s: float | None = None
    condition: str = "FSK 50 μM"
    title: str = "Stimulus response"


def _demo() -> StimulusFanInput:
    rng = np.random.default_rng(173)
    t = np.linspace(-20, 80, 220)
    traces = []
    for _ in range(40):
        amp = 0.3 + rng.normal(0, 0.08)
        tau = 8 + rng.uniform(-2, 3)
        resp = amp * np.tanh(np.clip(t / tau, 0, None))
        trace = 1.0 + resp + rng.normal(0, 0.015, t.size)
        traces.append(trace.tolist())
    return StimulusFanInput(
        t=t.tolist(),
        traces=traces,
        stim_duration_s=60.0,
    )


_META = RecipeMetadata(
    name="stimulus_response_fan",
    modality="fret_biosensors",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question="How does the per-cell FRET-ratio response fan out after a stimulus, and what is the mean envelope?",
    required_fields=("t", "traces"),
    optional_fields=("stim_duration_s", "condition", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("ratio_timecourse_hierarchical_ci",),
)


@register_recipe(metadata=_META, contract=StimulusFanInput, demo_contract=_demo)
def render(contract: StimulusFanInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)
    accent = palette.pick("donor")
    ratio_up = palette.pick("ratio_up")

    t = np.array(contract.t, dtype=float)
    traces = [np.array(tr, dtype=float) for tr in contract.traces]

    # Stimulus duration shading.
    if contract.stim_duration_s is not None:
        ax.axvspan(0, contract.stim_duration_s, color="#BBBBBB",
                   alpha=0.18, zorder=1)
        ax.text(contract.stim_duration_s / 2, ax.get_ylim()[1] if False else 1.4,
                f"stim ({smart_fmt(contract.stim_duration_s)} s)",
                ha="center", va="top", fontsize=6.6, color="#555555",
                bbox=dict(boxstyle="round,pad=0.14", fc="white",
                          ec="none", alpha=0.9),
                zorder=6)

    # Ratio-neutral reference.
    ax.axhline(1.0, color="#AAAAAA", lw=0.5, ls=":", zorder=2)

    # Fan of per-cell traces.
    for tr in traces:
        ax.plot(t, tr, color=accent, lw=0.5, alpha=0.3, zorder=3)

    # Mean + 10–90 percentile ribbon.
    if traces:
        stacked = np.vstack(traces)
        mean = stacked.mean(axis=0)
        lo = np.quantile(stacked, 0.10, axis=0)
        hi = np.quantile(stacked, 0.90, axis=0)
        ax.fill_between(t, lo, hi, color=ratio_up, alpha=0.15,
                        linewidth=0, zorder=4)
        ax.plot(t, mean, color=ratio_up, lw=1.4, zorder=5,
                label=f"mean (N={len(traces)})")

    ax.set_xlabel("time from stim (s)")
    ax.set_ylabel(r"F$_\mathrm{A}$/F$_\mathrm{D}$")
    ax.set_title(f"{contract.title} · {contract.condition}",
                 fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="upper left",
              handlelength=1.8)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
