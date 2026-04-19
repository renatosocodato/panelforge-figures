"""Skeleton kymograph — spatiotemporal intensity along a cell edge arc-length."""

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


class SkeletonKymoInput(RecipeContract):
    arc_length_um: list[float] = Field(...)
    time_s: list[float] = Field(...)
    intensity: list[list[float]] = Field(
        ..., description="2D array [time][arc] of filament intensity (a.u.)"
    )
    title: str = "Actin intensity kymograph"


def _demo() -> SkeletonKymoInput:
    rng = np.random.default_rng(499)
    arc = np.linspace(0, 60, 120)
    t = np.linspace(0, 300, 80)
    AA, TT = np.meshgrid(arc, t)
    # Waves of intensity sweeping along the edge (period ~120 s).
    waves = 1.2 * np.cos(2 * np.pi * (AA / 25 - TT / 120))
    pulses = 0.7 * np.exp(-((TT - 150) ** 2) / 1800)
    intensity_arr = 1.0 + 0.5 * waves + pulses + rng.normal(0, 0.08, AA.shape)
    intensity_arr = np.clip(intensity_arr, 0, None)
    return SkeletonKymoInput(
        arc_length_um=arc.tolist(),
        time_s=t.tolist(),
        intensity=intensity_arr.tolist(),
    )


_META = RecipeMetadata(
    name="skeleton_overlay_kymograph",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.heatmap,
    answers_question="How does filament intensity vary along the cell edge over time, and are there propagating waves?",
    required_fields=("arc_length_um", "time_s", "intensity"),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet", "tif"),
    alternatives_in_modality=("branch_point_density_map",),
)


@register_recipe(metadata=_META, contract=SkeletonKymoInput, demo_contract=_demo)
def render(contract: SkeletonKymoInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.4))
    AESTHETIC.apply_to_ax(ax)

    arc = np.array(contract.arc_length_um, dtype=float)
    t = np.array(contract.time_s, dtype=float)
    intensity_arr = np.array(contract.intensity, dtype=float)

    extent = (arc.min(), arc.max(), t.max(), t.min())
    im = ax.imshow(
        intensity_arr, extent=extent, cmap=AESTHETIC.continuous_cmap,
        aspect="auto", interpolation="bilinear",
    )

    # Mean intensity over time on right inset.
    ax_r = ax.inset_axes([1.02, 0, 0.14, 1.0], sharey=ax)
    ax_r.plot(intensity_arr.mean(axis=1), t, color="#333333", lw=0.9)
    ax_r.set_ylim(t.max(), t.min())
    ax_r.set_xlabel("mean", fontsize=6.0)
    ax_r.tick_params(axis="both", labelsize=5.8)
    ax_r.set_yticks([])

    cbar = ax.figure.colorbar(im, ax=[ax, ax_r], fraction=0.05, pad=0.08,
                              location="right")
    cbar.set_label("intensity (a.u.)", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)

    ax.set_xlabel(r"arc length along edge ($\mu$m)")
    ax.set_ylabel("time (s)")
    ax.set_title(
        f"{contract.title}  ·  range "
        f"{smart_fmt(float(intensity_arr.min()))}-"
        f"{smart_fmt(float(intensity_arr.max()))}",
        fontsize=9.0, pad=4,
    )
    return ax
