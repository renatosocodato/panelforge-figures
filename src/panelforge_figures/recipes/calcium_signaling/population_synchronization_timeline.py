"""Population synchronization coefficient over time.

Plots a scalar sync(t) (e.g., mean pairwise correlation, Golomb &
Rinzel index, or fraction of cells co-active in a bin) over the whole
recording. Distinct from the pairwise `synchronization_matrix`, which
collapses time to one matrix; this collapses cells to one curve.
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


class SyncTimelineInput(RecipeContract):
    time_s: list[float] = Field(..., min_length=3)
    sync_index: list[float] = Field(...)
    sync_sem: list[float] | None = None
    threshold: float | None = Field(
        default=0.6, description="sync level above which the population counts as 'synchronised'"
    )
    stim_times: list[float] = Field(default_factory=list)
    title: str = "Population synchronization"


def _demo() -> SyncTimelineInput:
    rng = np.random.default_rng(241)
    t = np.linspace(0, 80, 240)
    # Baseline sync ~0.3, episodes of high sync around stims.
    sig = 0.28 + 0.55 * np.exp(-((t - 20) / 4) ** 2) \
               + 0.50 * np.exp(-((t - 55) / 5) ** 2)
    sig = np.clip(sig + rng.normal(0, 0.03, t.size), 0, 1)
    sem = 0.04 * np.ones_like(t)
    return SyncTimelineInput(
        time_s=t.tolist(),
        sync_index=sig.tolist(),
        sync_sem=sem.tolist(),
        threshold=0.6,
        stim_times=[20.0, 55.0],
    )


_META = RecipeMetadata(
    name="population_synchronization_timeline",
    modality="calcium_signaling",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "How does a population-level synchronization coefficient evolve "
        "over time?"
    ),
    required_fields=("time_s", "sync_index"),
    optional_fields=("sync_sem", "threshold", "stim_times", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("synchronization_matrix",),
)


@register_recipe(
    metadata=_META,
    contract=SyncTimelineInput,
    demo_contract=_demo,
)
def render(contract: SyncTimelineInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.2))
    AESTHETIC.apply_to_ax(ax)

    t = np.asarray(contract.time_s, float)
    s = np.asarray(contract.sync_index, float)
    sem = (np.asarray(contract.sync_sem, float)
           if contract.sync_sem is not None else None)

    main_color = "#2E7D32"
    thr_color = "#D32F2F"

    if sem is not None:
        ax.fill_between(t, s - sem / 2, s + sem / 2,
                        color=main_color, alpha=0.18, linewidth=0, zorder=2)
    ax.plot(t, s, color=main_color, lw=1.2, zorder=3, label="sync index")

    # Threshold line + above-threshold shading.
    if contract.threshold is not None:
        ax.axhline(contract.threshold, color=thr_color, lw=0.8, ls="--",
                   zorder=2, label=f"threshold = {smart_fmt(contract.threshold)}")
        above = s >= contract.threshold
        ax.fill_between(t, s, contract.threshold,
                        where=above, interpolate=True,
                        color=thr_color, alpha=0.18, zorder=1)

    # Stim markers.
    for i, st in enumerate(contract.stim_times):
        lbl = "stim" if i == 0 else None
        ax.axvline(st, color="#111111", lw=0.6, ls=":",
                   zorder=4, label=lbl)

    ax.set_xlabel("time (s)")
    ax.set_ylabel("sync index")
    ax.set_xlim(t.min(), t.max())
    ax.set_ylim(0, 1.05)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.6)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    if contract.threshold is not None:
        frac_above = float(np.mean(s >= contract.threshold))
        peak = float(s.max())
        ax.text(0.01, 0.97,
                f"peak = {smart_fmt(peak)}\n"
                f"{smart_fmt(frac_above * 100)}% of time above threshold",
                transform=ax.transAxes, ha="left", va="top",
                fontsize=6.4, color="#333333",
                bbox=dict(boxstyle="round,pad=0.18", fc="white",
                          ec="#BBBBBB", lw=0.5, alpha=0.92),
                zorder=6)
    return ax
