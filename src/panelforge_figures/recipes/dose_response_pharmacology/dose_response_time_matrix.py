"""Concentration × time response matrix with peak-time isochrone."""

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


class DoseTimeMatrixInput(RecipeContract):
    concentrations_M: list[float] = Field(..., min_length=3)
    time_min: list[float] = Field(..., min_length=3)
    response: list[list[float]] = Field(
        ..., description="n_conc × n_time response matrix"
    )
    y_label: str = "response"
    title: str = "Dose × time response"


def _demo() -> DoseTimeMatrixInput:
    rng = np.random.default_rng(131)
    conc = np.logspace(-9, -5, 8)
    t = np.linspace(0, 60, 30)
    CC, TT = np.meshgrid(conc, t, indexing="ij")
    # Response grows with conc, peaks at t ~ 20 min, decays.
    amp = 100 / (1 + (1e-7 / CC) ** 1.2)
    R = amp * np.exp(-((TT - 20) / 10) ** 2)
    R += rng.normal(0, 2.0, R.shape)
    return DoseTimeMatrixInput(
        concentrations_M=conc.tolist(),
        time_min=t.tolist(),
        response=R.tolist(),
    )


_META = RecipeMetadata(
    name="dose_response_time_matrix",
    modality="dose_response_pharmacology",
    family=RecipeFamily.heatmap,
    answers_question=(
        "Over a concentration × time grid, when and at what "
        "concentration does the effect peak?"
    ),
    required_fields=("concentrations_M", "time_min", "response"),
    optional_fields=("y_label", "title"),
    file_format_hints=("csv", "parquet", "npz"),
    alternatives_in_modality=("hill_fit_with_ci", "drug_combo_heatmap"),
)


@register_recipe(
    metadata=_META,
    contract=DoseTimeMatrixInput,
    demo_contract=_demo,
)
def render(contract: DoseTimeMatrixInput, ax=None, **_):
    import matplotlib as mpl

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.6))
    AESTHETIC.apply_to_ax(ax)

    conc = np.asarray(contract.concentrations_M, float)
    t = np.asarray(contract.time_min, float)
    R = np.asarray(contract.response, float)

    cmap = mpl.colormaps["viridis"]
    vmax = float(np.nanmax(R))
    im = ax.imshow(
        R, origin="lower", cmap=cmap, aspect="auto",
        vmin=0.0, vmax=max(vmax, 1e-9),
        extent=(t[0], t[-1], 0, conc.size),
        interpolation="nearest",
    )
    ax.set_yticks(np.arange(conc.size) + 0.5)
    ax.set_yticklabels([f"{v:.0e}" for v in conc], fontsize=6.4)

    # Peak-time isochrone — the time at which each conc row peaks.
    peak_idx = np.argmax(R, axis=1)
    peak_times = t[peak_idx]
    ax.plot(peak_times, np.arange(conc.size) + 0.5, color="white",
            lw=1.2, zorder=4, label="per-conc peak")

    # Global peak marker.
    i_max, j_max = np.unravel_index(int(np.argmax(R)), R.shape)
    ax.scatter([t[j_max]], [i_max + 0.5], s=90, marker="*",
               color="#D32F2F", edgecolor="white", linewidth=1.0,
               zorder=5)

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(contract.y_label, fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    ax.set_xlabel("time (min)")
    ax.set_ylabel("concentration (M)")
    ax.set_title(
        f"{contract.title}  ·  peak at {smart_fmt(conc[i_max] * 1e9)} nM, "
        f"t = {smart_fmt(t[j_max])} min",
        fontsize=8.6, pad=4,
    )
    ax.legend(fontsize=6.4, frameon=False, loc="lower right",
              handlelength=1.4)
    return ax
