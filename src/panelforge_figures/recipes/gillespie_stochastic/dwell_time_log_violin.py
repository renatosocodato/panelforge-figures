"""Dwell-time log-violin — per-state distributions on log₁₀ seconds."""

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


class DwellViolinInput(RecipeContract):
    state_dwells: dict[str, list[float]] = Field(
        ..., description="state → list of dwell times in seconds (must be >0)"
    )
    title: str = "Dwell times per state"


def _demo() -> DwellViolinInput:
    rng = np.random.default_rng(107)
    return DwellViolinInput(
        state_dwells={
            "HOME": rng.exponential(4.0, 800).tolist(),
            "GATE": rng.exponential(12.0, 400).tolist(),
            "TRAP": rng.exponential(45.0, 200).tolist(),
        },
    )


_META = RecipeMetadata(
    name="dwell_time_log_violin",
    modality="gillespie_stochastic",
    family=RecipeFamily.split_violin,
    answers_question="How are dwell times per state distributed on a log scale, and what are the medians and spreads?",
    required_fields=("state_dwells",),
    optional_fields=("title",),
    file_format_hints=("parquet", "csv"),
    alternatives_in_modality=("waiting_time_ecdf_fitted",),
)


@register_recipe(metadata=_META, contract=DwellViolinInput, demo_contract=_demo)
def render(contract: DwellViolinInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    states = list(contract.state_dwells.keys())
    positions = list(range(len(states)))
    log_data = []
    for s in states:
        vals = np.array(contract.state_dwells[s], dtype=float)
        vals = vals[vals > 0]
        log_data.append(np.log10(vals) if vals.size else np.array([0.0]))

    parts = ax.violinplot(
        log_data, positions=positions, widths=0.72,
        showmeans=False, showmedians=False, showextrema=False,
    )
    for i, pc in enumerate(parts["bodies"]):
        s = states[i]
        color = palette.pick(s) if s in palette.semantic else palette[i]
        pc.set_facecolor(color)
        pc.set_edgecolor("#333333")
        pc.set_alpha(0.55)
        pc.set_linewidth(0.6)

    # Quartile bars + median dots.
    for pos, logv, s in zip(positions, log_data, states):
        if logv.size < 4:
            continue
        q1, med, q3 = np.quantile(logv, [0.25, 0.5, 0.75])
        color = palette.pick(s) if s in palette.semantic else palette[pos]
        ax.plot([pos, pos], [q1, q3], color="black", lw=3.0, solid_capstyle="butt",
                zorder=4)
        ax.scatter([pos], [med], s=36, facecolor="white",
                   edgecolor="black", linewidth=1.0, zorder=5)
        # Per-state label with median dwell.
        ax.text(pos, q3 + 0.10,
                f"median = {smart_fmt(10 ** med)} s",
                ha="center", va="bottom",
                fontsize=6.4, color=color,
                bbox=dict(boxstyle="round,pad=0.16", fc="white",
                          ec="none", alpha=0.92),
                zorder=6)

    ax.set_xticks(positions)
    ax.set_xticklabels(states, fontsize=7.4)
    ax.set_ylabel(r"$\log_{10}$ dwell (s)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # N counts below each violin.
    y_low = min(d.min() for d in log_data) - 0.12
    for pos, s in zip(positions, states):
        ax.text(pos, y_low,
                f"N = {len(contract.state_dwells[s])}",
                ha="center", va="top", fontsize=6.2, color="#666666")
    ax.margins(y=0.08)
    return ax
