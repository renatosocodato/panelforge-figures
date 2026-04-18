"""Ratio timecourse with hierarchical CI — mean + per-condition CI ribbons."""

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


class RatioTimecourseInput(RecipeContract):
    t: list[float] = Field(...)
    conditions: dict[str, dict[str, list[float]]] = Field(
        ..., description="condition → {mean, lo, hi} aligned to t"
    )
    stim_time_s: float | None = None
    y_label: str = r"F$_\mathrm{A}$/F$_\mathrm{D}$"
    title: str = "Ratio timecourse"


def _demo() -> RatioTimecourseInput:
    rng = np.random.default_rng(167)
    t = np.linspace(-30, 120, 150)
    conditions: dict[str, dict[str, list[float]]] = {}
    for name, amp, delay, color_idx in [
        ("vehicle", 0.05, 0.0, 0),
        ("+ FSK (50 μM)", 0.45, 2.0, 1),
        ("+ FSK + H89", 0.12, 2.0, 2),
    ]:
        resp = amp * np.tanh(np.clip((t - delay) / 8, 0, None))
        mean = 1.0 + resp + rng.normal(0, 0.01, t.size)
        width = 0.04 + 0.01 * np.abs(t - delay) / 60
        lo = mean - width
        hi = mean + width
        conditions[name] = {"mean": mean.tolist(),
                            "lo": lo.tolist(),
                            "hi": hi.tolist()}
    return RatioTimecourseInput(
        t=t.tolist(),
        conditions=conditions,
        stim_time_s=0.0,
    )


_META = RecipeMetadata(
    name="ratio_timecourse_hierarchical_ci",
    modality="fret_biosensors",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question="How does the FRET ratio evolve over time across conditions, with hierarchical (cell-in-animal) uncertainty?",
    required_fields=("t", "conditions"),
    optional_fields=("stim_time_s", "y_label", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("stimulus_response_fan", "single_cell_ratio_trajectories"),
)


@register_recipe(metadata=_META, contract=RatioTimecourseInput, demo_contract=_demo)
def render(contract: RatioTimecourseInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)
    fallback = ["#00BFA5", "#FFB300", "#D84315", "#1565C0"]

    t = np.array(contract.t, dtype=float)
    # Stimulus bar.
    if contract.stim_time_s is not None:
        ax.axvline(contract.stim_time_s, color="#888888", lw=0.7, ls="--", zorder=1)
        ax.text(contract.stim_time_s, ax.get_ylim()[1] if False else 1.005,
                "stim", ha="left", va="bottom", fontsize=6.4, color="#555555",
                bbox=dict(boxstyle="round,pad=0.14", fc="white",
                          ec="none", alpha=0.9), zorder=6)

    # Ratio-neutral reference.
    ax.axhline(1.0, color="#AAAAAA", lw=0.5, ls=":", zorder=2)

    for i, (name, data) in enumerate(contract.conditions.items()):
        color = fallback[i % len(fallback)]
        mean = np.array(data["mean"], dtype=float)
        lo = np.array(data["lo"], dtype=float)
        hi = np.array(data["hi"], dtype=float)
        ax.fill_between(t, lo, hi, color=color, alpha=0.18,
                        linewidth=0, zorder=3)
        ax.plot(t, mean, color=color, lw=1.2, label=name, zorder=4)

    ax.set_xlabel("time (s)")
    ax.set_ylabel(contract.y_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="upper left",
              handlelength=1.8)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    _ = palette
    return ax
