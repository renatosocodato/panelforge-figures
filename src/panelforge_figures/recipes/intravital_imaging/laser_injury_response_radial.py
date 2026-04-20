"""Radial response to a laser ablation, time-resolved.

At distance r from the ablation site (r=0), the cellular response
(chemotaxis index, density, intensity) is plotted as curves over time
with CI bands. A t=0 baseline is overlaid as a reference. Colour
encodes time since injury.
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


class LaserInjuryInput(RecipeContract):
    r_um: list[float] = Field(..., min_length=3)
    time_min: list[float] = Field(..., min_length=2)
    response: list[list[float]] = Field(
        ..., description="n_time × n_r matrix of response values"
    )
    ci_lo: list[list[float]] | None = None
    ci_hi: list[list[float]] | None = None
    response_label: str = "chemotaxis index"
    title: str = "Laser-injury radial response"


def _demo() -> LaserInjuryInput:
    rng = np.random.default_rng(941)
    r = np.linspace(0, 150, 25)
    t = [0, 5, 10, 15, 30, 60]
    resp = np.zeros((len(t), r.size))
    for i, ti in enumerate(t):
        # Peak forms at r ~ 15-25 μm and grows then relaxes.
        amp = 1.2 * (1 - np.exp(-ti / 12)) * np.exp(-ti / 90)
        resp[i] = amp * np.exp(-((r - 20) ** 2) / (2 * 22 ** 2))
        resp[i] += rng.normal(0, 0.02, r.size)
    ci = 0.04 * np.ones_like(resp)
    return LaserInjuryInput(
        r_um=r.tolist(),
        time_min=t,
        response=resp.tolist(),
        ci_lo=(resp - ci / 2).tolist(),
        ci_hi=(resp + ci / 2).tolist(),
    )


_META = RecipeMetadata(
    name="laser_injury_response_radial",
    modality="intravital_imaging",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question=(
        "At distance r from an ablation site, how does the cellular "
        "response curve evolve over time?"
    ),
    required_fields=("r_um", "time_min", "response"),
    optional_fields=("ci_lo", "ci_hi", "response_label", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("vessel_diameter_kymograph",),
)


@register_recipe(
    metadata=_META,
    contract=LaserInjuryInput,
    demo_contract=_demo,
)
def render(contract: LaserInjuryInput, ax=None, **_):
    import matplotlib as mpl

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.6))
    AESTHETIC.apply_to_ax(ax)

    r = np.asarray(contract.r_um, float)
    t = np.asarray(contract.time_min, float)
    R = np.asarray(contract.response, float)
    lo = (np.asarray(contract.ci_lo, float)
          if contract.ci_lo is not None else None)
    hi = (np.asarray(contract.ci_hi, float)
          if contract.ci_hi is not None else None)

    cmap = mpl.colormaps[AESTHETIC.continuous_cmap]
    tmax = max(t.max(), 1.0)

    peak_info = []
    for i, ti in enumerate(t):
        color = cmap(0.15 + 0.75 * ti / tmax)
        if lo is not None and hi is not None:
            ax.fill_between(r, lo[i], hi[i], color=color, alpha=0.18,
                            linewidth=0, zorder=2)
        ax.plot(r, R[i], color=color, lw=1.2, zorder=3,
                label=f"t = {smart_fmt(ti)} min")
        # Track peak position.
        pk = int(np.argmax(R[i]))
        peak_info.append((float(ti), float(r[pk]), float(R[i, pk])))

    # t=0 baseline reference.
    ax.plot(r, R[0], color="#111111", lw=0.6, ls="--", zorder=4,
            label="t = 0 baseline")

    ax.set_xlabel("distance from ablation r (μm)")
    ax.set_ylabel(contract.response_label)
    ax.set_xlim(r.min(), r.max())
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.6)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Peak-position vs time callout.
    _, peak_r, _ = zip(*peak_info)
    peak_r_mean = float(np.mean(peak_r))
    peak_r_max_t = max(peak_info, key=lambda it: it[2])
    fig = ax.figure
    fig.text(
        0.5, -0.16,
        f"peak response near r = {smart_fmt(peak_r_mean)} μm  ·  "
        f"max at t = {smart_fmt(peak_r_max_t[0])} min "
        f"(r = {smart_fmt(peak_r_max_t[1])} μm)",
        ha="center", va="top", fontsize=6.6, color="#333333",
        transform=ax.transAxes,
        bbox=dict(boxstyle="round,pad=0.22", fc="white",
                  ec=AESTHETIC.annotation_style.callout_accent, lw=0.5),
    )
    return ax
