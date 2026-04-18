"""Ratio heatmap over field — 2D FRET ratio image with scale bar and colorbar."""

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


class RatioFieldInput(RecipeContract):
    x_um: list[float]
    y_um: list[float]
    ratio: list[list[float]] = Field(
        ..., description="ratio[j][i] at (x_um[i], y_um[j])"
    )
    stim_state: str = "pre-stim"
    time_post_stim_s: float | None = None
    sensor_name: str = "ExRai-AKAR"
    title: str = "FRET ratio field"


def _demo() -> RatioFieldInput:
    rng = np.random.default_rng(163)
    x = np.linspace(0, 80, 100)
    y = np.linspace(0, 60, 80)
    X, Y = np.meshgrid(x, y)
    # Gradient + two hotspots + noise.
    ratio = (
        1.0
        + 0.3 * np.exp(-((X - 20) ** 2 + (Y - 18) ** 2) / 120)
        + 0.2 * np.exp(-((X - 55) ** 2 + (Y - 40) ** 2) / 220)
        - 0.05 * Y / 60
        + rng.normal(0, 0.015, X.shape)
    )
    return RatioFieldInput(
        x_um=x.tolist(),
        y_um=y.tolist(),
        ratio=ratio.tolist(),
        stim_state="post-stim",
        time_post_stim_s=30.0,
        sensor_name="ExRai-AKAR",
        title="AKAR ratio · 30 s post-stim",
    )


_META = RecipeMetadata(
    name="ratio_heatmap_over_field",
    modality="fret_biosensors",
    family=RecipeFamily.heatmap,
    answers_question="What is the spatial pattern of FRET ratio across the imaging field at a given timepoint?",
    required_fields=("x_um", "y_um", "ratio"),
    optional_fields=("stim_state", "time_post_stim_s", "sensor_name", "title"),
    file_format_hints=("tif", "npz", "parquet"),
    alternatives_in_modality=("roi_ratio_summary_grid", "fret_signal_to_noise_map"),
)


@register_recipe(metadata=_META, contract=RatioFieldInput, demo_contract=_demo)
def render(contract: RatioFieldInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)

    R = np.array(contract.ratio, dtype=float)
    vmax = max(abs(R.max() - 1.0), abs(R.min() - 1.0))
    im = ax.imshow(
        R, origin="lower", cmap=AESTHETIC.ratio_cmap or "RdBu_r",
        vmin=1 - vmax, vmax=1 + vmax,
        extent=(contract.x_um[0], contract.x_um[-1],
                contract.y_um[0], contract.y_um[-1]),
        aspect="equal", interpolation="nearest",
    )

    # Stimulus / timepoint annotation upper-left.
    tag_lines = [f"sensor: {contract.sensor_name}", f"state: {contract.stim_state}"]
    if contract.time_post_stim_s is not None:
        tag_lines.append(f"t = +{smart_fmt(contract.time_post_stim_s)} s")
    ax.text(0.02, 0.97, "\n".join(tag_lines),
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.6, color="white",
            bbox=dict(boxstyle="round,pad=0.20", fc="#333333",
                      ec="none", alpha=0.72),
            zorder=5)

    # Scale bar (20 μm).
    x_sb = contract.x_um[0] + 0.06 * (contract.x_um[-1] - contract.x_um[0])
    y_sb = contract.y_um[0] + 0.08 * (contract.y_um[-1] - contract.y_um[0])
    ax.plot([x_sb, x_sb + 20], [y_sb, y_sb],
            color="white", lw=2.5, solid_capstyle="butt", zorder=6)
    ax.text(x_sb + 10, y_sb + 2, "20 μm",
            ha="center", va="bottom", fontsize=6.4, color="white",
            bbox=dict(boxstyle="round,pad=0.14", fc="#333333",
                      ec="none", alpha=0.65))

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(r"F$_\mathrm{A}$/F$_\mathrm{D}$", fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    ax.set_xlabel("x (μm)")
    ax.set_ylabel("y (μm)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.set_xticks([])
    ax.set_yticks([])
    return ax
