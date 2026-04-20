"""τ-leaping vs exact-SSA trajectory comparison with residual overlay.

Plots the exact-SSA trajectory and a τ-leaping approximation on the
same axis, with a thin strip beneath showing the residual (τ − exact)
over time. A speedup factor (exact_wall / leap_wall) is displayed as a
corner callout.
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


class TauLeapingInput(RecipeContract):
    time_s: list[float] = Field(..., min_length=3)
    exact_trace: list[float] = Field(...)
    tau_leap_trace: list[float] = Field(...)
    tau_leap_step: float = 0.1
    speedup_factor: float | None = None
    species_label: str = "molecule count"
    title: str = "τ-leaping vs exact SSA"


def _demo() -> TauLeapingInput:
    rng = np.random.default_rng(83)
    t = np.linspace(0, 20, 600)
    # Exact: smoother after many events.
    exact = 20 + 4 * np.cumsum(rng.normal(0, 0.08, t.size))
    # τ-leap: slightly offset / smoother.
    leap = exact + 0.18 * np.sin(t * 1.1) + rng.normal(0, 0.25, t.size)
    return TauLeapingInput(
        time_s=t.tolist(),
        exact_trace=exact.tolist(),
        tau_leap_trace=leap.tolist(),
        tau_leap_step=0.1,
        speedup_factor=12.4,
    )


_META = RecipeMetadata(
    name="tau_leaping_comparison",
    modality="gillespie_stochastic",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "How close does a τ-leaping approximation stay to the exact "
        "SSA trajectory, and how does error accumulate over t?"
    ),
    required_fields=("time_s", "exact_trace", "tau_leap_trace"),
    optional_fields=(
        "tau_leap_step", "speedup_factor", "species_label", "title",
    ),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("trajectory_fan_with_fpt",),
)


@register_recipe(
    metadata=_META,
    contract=TauLeapingInput,
    demo_contract=_demo,
)
def render(contract: TauLeapingInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.6))
    AESTHETIC.apply_to_ax(ax)

    t = np.asarray(contract.time_s, float)
    y_exact = np.asarray(contract.exact_trace, float)
    y_leap = np.asarray(contract.tau_leap_trace, float)
    residual = y_leap - y_exact

    # Main trajectory panel (upper ~75% of axis using axes fraction).
    # We'll draw residual below via a secondary inset inside the axes.
    # Trajectories.
    ax.step(t, y_exact, where="post", color="#111111", lw=1.1,
            zorder=3, label="exact SSA")
    ax.step(t, y_leap, where="post", color="#D32F2F", lw=1.1,
            alpha=0.85, zorder=4,
            label=f"τ-leap (τ={smart_fmt(contract.tau_leap_step)})")

    # Main axis: keep tick labels but hide xlabel (the residual inset
    # carries its own "time (s)" axis below).
    ax.tick_params(axis="x", labelbottom=False)
    ax.set_ylabel(contract.species_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.set_xlim(t.min(), t.max())
    ax.legend(fontsize=6.6, frameon=False, loc="upper left",
              handlelength=1.8)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Residual strip — inset axes below main.
    resid_ax = ax.inset_axes([0.0, -0.40, 1.0, 0.24])
    resid_ax.plot(t, residual, color="#6A1B9A", lw=0.9, zorder=3)
    resid_ax.axhline(0, color="#888888", lw=0.6, ls="--", zorder=1)
    resid_ax.set_xlim(t.min(), t.max())
    resid_ax.set_xlabel("time (s)", fontsize=7.0)
    resid_ax.set_ylabel("τ − exact", fontsize=6.6)
    resid_ax.tick_params(labelsize=6.2)
    resid_ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    resid_ax.set_axisbelow(True)

    # Error and speedup callout.
    rmse = float(np.sqrt(np.mean(residual ** 2)))
    bits = [f"RMSE = {smart_fmt(rmse)}"]
    if contract.speedup_factor is not None:
        bits.append(f"speedup × {smart_fmt(float(contract.speedup_factor))}")
    ax.text(0.98, 0.97, "  ·  ".join(bits),
            transform=ax.transAxes, ha="right", va="top",
            fontsize=6.6, color="#111111",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.95),
            zorder=6)
    return ax
