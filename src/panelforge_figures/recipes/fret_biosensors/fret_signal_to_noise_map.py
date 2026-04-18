"""FRET signal-to-noise map — per-pixel SNR with threshold overlay."""

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


class SNRMapInput(RecipeContract):
    x_um: list[float]
    y_um: list[float]
    snr: list[list[float]] = Field(..., description="signal / noise ratio per pixel")
    snr_threshold: float = 3.0
    pixel_size_um: float = 0.2
    title: str = "FRET signal-to-noise"


def _demo() -> SNRMapInput:
    rng = np.random.default_rng(199)
    x = np.linspace(0, 100, 120)
    y = np.linspace(0, 80, 96)
    X, Y = np.meshgrid(x, y)
    # Broad SNR pattern: higher near cell bodies, noisy background.
    snr = (
        1.5
        + 5.0 * np.exp(-((X - 45) ** 2 + (Y - 35) ** 2) / 800)
        + 3.0 * np.exp(-((X - 75) ** 2 + (Y - 55) ** 2) / 400)
        + rng.normal(0, 0.4, X.shape)
    )
    return SNRMapInput(
        x_um=x.tolist(),
        y_um=y.tolist(),
        snr=np.clip(snr, 0, None).tolist(),
        snr_threshold=3.0,
    )


_META = RecipeMetadata(
    name="fret_signal_to_noise_map",
    modality="fret_biosensors",
    family=RecipeFamily.heatmap,
    answers_question="Where in the imaging field is FRET signal quality usable, and what fraction of pixels clear the SNR threshold?",
    required_fields=("x_um", "y_um", "snr"),
    optional_fields=("snr_threshold", "pixel_size_um", "title"),
    file_format_hints=("tif", "npz"),
    alternatives_in_modality=("ratio_heatmap_over_field",),
)


@register_recipe(metadata=_META, contract=SNRMapInput, demo_contract=_demo)
def render(contract: SNRMapInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)

    S = np.array(contract.snr, dtype=float)
    im = ax.imshow(
        S, origin="lower", cmap=AESTHETIC.continuous_cmap,
        extent=(contract.x_um[0], contract.x_um[-1],
                contract.y_um[0], contract.y_um[-1]),
        aspect="equal", interpolation="nearest",
        vmin=0, vmax=np.quantile(S, 0.995),
    )
    # Threshold contour.
    X, Y = np.meshgrid(contract.x_um, contract.y_um)
    ax.contour(X, Y, S, levels=[contract.snr_threshold],
               colors="white", linewidths=1.0, zorder=4)

    good_frac = float((S >= contract.snr_threshold).mean())

    # Scale bar.
    x_sb = contract.x_um[0] + 0.05 * (contract.x_um[-1] - contract.x_um[0])
    y_sb = contract.y_um[0] + 0.07 * (contract.y_um[-1] - contract.y_um[0])
    ax.plot([x_sb, x_sb + 20], [y_sb, y_sb],
            color="white", lw=2.5, solid_capstyle="butt", zorder=5)
    ax.text(x_sb + 10, y_sb + 2, "20 μm",
            ha="center", va="bottom", fontsize=6.4, color="white",
            bbox=dict(boxstyle="round,pad=0.14", fc="#333333",
                      ec="none", alpha=0.65))

    ax.text(0.99, 0.97,
            f"{100 * good_frac:.0f}% pixels ≥ {smart_fmt(contract.snr_threshold)}",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=6.6, color="white",
            bbox=dict(boxstyle="round,pad=0.18", fc="#333333",
                      ec="none", alpha=0.7),
            zorder=6)

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("SNR", fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("x (μm)")
    ax.set_ylabel("y (μm)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    return ax
