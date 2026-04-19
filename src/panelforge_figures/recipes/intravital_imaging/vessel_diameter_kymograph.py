"""Vessel-diameter kymograph — diameter along a blood vessel over time."""

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


class VesselKymoInput(RecipeContract):
    position_um: list[float] = Field(...)
    time_s: list[float] = Field(...)
    diameter_um: list[list[float]] = Field(
        ..., description="2D array [time][position] of vessel diameter",
    )
    title: str = "Vessel diameter kymograph"


def _demo() -> VesselKymoInput:
    rng = np.random.default_rng(467)
    pos = np.linspace(0, 400, 80)
    t = np.linspace(0, 120, 60)
    PP, TT = np.meshgrid(pos, t)
    # Baseline with a vasodilation wave arriving at t ~ 40 s.
    base = 8 + 0.01 * PP
    pulse = 2.5 * np.exp(-((TT - 50) ** 2) / 200) * np.exp(-((PP - 200) ** 2) / 8000)
    noise = rng.normal(0, 0.15, PP.shape)
    diam = base + pulse + noise
    return VesselKymoInput(
        position_um=pos.tolist(),
        time_s=t.tolist(),
        diameter_um=diam.tolist(),
    )


_META = RecipeMetadata(
    name="vessel_diameter_kymograph",
    modality="intravital_imaging",
    family=RecipeFamily.heatmap,
    answers_question="How does vessel diameter vary along its length and over time (e.g. propagating vasodilation)?",
    required_fields=("position_um", "time_s", "diameter_um"),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet", "tif"),
    alternatives_in_modality=("two_photon_depth_projection",),
)


@register_recipe(metadata=_META, contract=VesselKymoInput, demo_contract=_demo)
def render(contract: VesselKymoInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.4))
    AESTHETIC.apply_to_ax(ax)

    pos = np.array(contract.position_um, dtype=float)
    t = np.array(contract.time_s, dtype=float)
    D = np.array(contract.diameter_um, dtype=float)

    extent = (pos.min(), pos.max(), t.max(), t.min())
    im = ax.imshow(
        D, extent=extent, cmap=AESTHETIC.continuous_cmap,
        aspect="auto", interpolation="bilinear",
    )

    # Time-averaged diameter on right panel (inline mini-profile).
    ax_r = ax.inset_axes([1.02, 0, 0.14, 1.0], sharey=ax)
    mean_d = D.mean(axis=1)
    ax_r.plot(mean_d, t, color="#333333", lw=0.9)
    ax_r.set_ylim(t.max(), t.min())
    ax_r.set_xlabel(r"$\mu$m", fontsize=6.0)
    ax_r.tick_params(axis="both", labelsize=5.8)
    ax_r.set_yticks([])

    cbar = ax.figure.colorbar(im, ax=[ax, ax_r], fraction=0.05, pad=0.08,
                              location="right")
    cbar.set_label(r"diameter ($\mu$m)", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)

    ax.set_xlabel(r"position along vessel ($\mu$m)")
    ax.set_ylabel("time (s)")
    ax.set_title(
        f"{contract.title}  ·  peak $\\Delta d$ = {smart_fmt(float(D.max() - D.min()))} $\\mu$m",
        fontsize=8.4, pad=4,
    )
    return ax
