"""Peri-event time histogram (PETH) aligned to Ca²⁺ event onsets.

Histograms the probability of observing another event at lag τ from
a reference onset (per-cell or pooled), with a ±CI shaded band and a
τ = 0 reference. Distinct from `spike_triggered_average`, which shows
the continuous ΔF/F waveform averaged around spikes.
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


class PETHInput(RecipeContract):
    lag_s: list[float] = Field(..., min_length=3)
    rate_by_group: dict[str, list[float]] = Field(
        ..., description="group → rate at each lag (events / s / cell)"
    )
    ci_by_group: dict[str, list[float]] | None = None
    baseline_rate: float | None = None
    title: str = "Peri-event time histogram"


def _demo() -> PETHInput:
    rng = np.random.default_rng(179)
    lag = np.linspace(-5.0, 10.0, 60)
    # Rebound bump around lag=1-3 s.
    bump = 0.6 * np.exp(-((lag - 2.0) / 1.4) ** 2)
    noise = rng.normal(0, 0.04, lag.size)
    return PETHInput(
        lag_s=lag.tolist(),
        rate_by_group={
            "control": (0.25 + bump + noise).tolist(),
            "TTX":     (0.15 + 0.3 * bump + rng.normal(0, 0.04, lag.size)).tolist(),
        },
        ci_by_group={
            "control": (0.05 * np.ones_like(lag)).tolist(),
            "TTX":     (0.04 * np.ones_like(lag)).tolist(),
        },
        baseline_rate=0.22,
    )


_META = RecipeMetadata(
    name="calcium_event_onset_alignment",
    modality="calcium_signaling",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question=(
        "Aligned to each Ca²⁺ event onset (PETH), what is the per-cell "
        "event probability vs lag?"
    ),
    required_fields=("lag_s", "rate_by_group"),
    optional_fields=("ci_by_group", "baseline_rate", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("spike_triggered_average", "event_raster_with_rate"),
)


@register_recipe(
    metadata=_META,
    contract=PETHInput,
    demo_contract=_demo,
)
def render(contract: PETHInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    lag = np.asarray(contract.lag_s, float)
    ci_by = contract.ci_by_group or {}

    for i, (name, vals) in enumerate(contract.rate_by_group.items()):
        v = np.asarray(vals, float)
        color = palette[i % len(palette.colors)]
        ci = np.asarray(ci_by.get(name, []), float) if ci_by else None
        if ci is not None and ci.size == v.size:
            ax.fill_between(lag, v - ci / 2, v + ci / 2,
                            color=color, alpha=0.20, linewidth=0, zorder=2)
        ax.plot(lag, v, color=color, lw=1.3, zorder=3, label=name)
        # Peak marker.
        pk = int(np.argmax(v))
        ax.scatter([lag[pk]], [v[pk]], s=22, color=color,
                   edgecolor="white", linewidth=0.6, zorder=4)

    # τ = 0 reference.
    ax.axvline(0, color="#111111", lw=0.8, zorder=1, label="event onset")
    # Baseline rate reference.
    if contract.baseline_rate is not None:
        ax.axhline(contract.baseline_rate, color="#888888",
                   lw=0.6, ls="--", zorder=1,
                   label=f"baseline = {smart_fmt(contract.baseline_rate)}")

    ax.set_xlabel(r"lag $\tau$ (s)")
    ax.set_ylabel("rate (events / s / cell)")
    ax.set_xlim(lag.min(), lag.max())
    ax.set_ylim(bottom=0)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.6)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
