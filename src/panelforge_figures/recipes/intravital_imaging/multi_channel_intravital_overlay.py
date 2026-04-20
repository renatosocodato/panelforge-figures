"""Multi-channel intravital RGB overlay with per-channel histogram sidebar.

Composites up to three channels (R, G, B) from the intravital field
into one RGB image with a mandatory scale bar. A small per-channel
histogram strip is drawn in the top-right corner so the reader can
assess per-channel exposure at a glance.
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


class MultiChannelOverlayInput(RecipeContract):
    red_channel: list[list[float]] = Field(
        ..., description="2-D array, intensity 0-1"
    )
    green_channel: list[list[float]] = Field(...)
    blue_channel: list[list[float]] = Field(...)
    pixel_size_um: float = 0.5
    channel_labels: tuple[str, str, str] = ("red", "green", "blue")
    title: str = "Intravital RGB overlay"


def _demo() -> MultiChannelOverlayInput:
    rng = np.random.default_rng(1013)
    H, W = 120, 160
    yy, xx = np.mgrid[:H, :W]

    def blobs(n, sigma_range):
        img = np.zeros((H, W), dtype=float)
        for _ in range(n):
            cx = rng.integers(10, W - 10)
            cy = rng.integers(10, H - 10)
            s = rng.uniform(*sigma_range)
            amp = rng.uniform(0.4, 1.0)
            img += amp * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * s ** 2))
        img += rng.normal(0, 0.02, img.shape)
        return np.clip(img / max(img.max(), 1e-9), 0, 1)

    R = blobs(30, (3, 6))
    G = blobs(18, (4, 8))
    B = blobs(25, (2, 4))
    return MultiChannelOverlayInput(
        red_channel=R.tolist(),
        green_channel=G.tolist(),
        blue_channel=B.tolist(),
        pixel_size_um=0.5,
        channel_labels=("CX3CR1-GFP (R)", "CCR2 (G)", "nuclei (B)"),
    )


_META = RecipeMetadata(
    name="multi_channel_intravital_overlay",
    modality="intravital_imaging",
    family=RecipeFamily.heatmap,
    answers_question=(
        "How do two (or more) intravital channels co-register across "
        "a field, with a shared scale-bar?"
    ),
    required_fields=("red_channel", "green_channel", "blue_channel"),
    optional_fields=("pixel_size_um", "channel_labels", "title"),
    file_format_hints=("npz", "tif"),
    alternatives_in_modality=(
        "two_photon_depth_projection",
        "depth_projected_microglia_field",
    ),
)


@register_recipe(
    metadata=_META,
    contract=MultiChannelOverlayInput,
    demo_contract=_demo,
)
def render(contract: MultiChannelOverlayInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 4.0))
    AESTHETIC.apply_to_ax(ax)

    R = np.asarray(contract.red_channel, float)
    G = np.asarray(contract.green_channel, float)
    B = np.asarray(contract.blue_channel, float)
    # Stack into RGB (H, W, 3).
    rgb = np.stack([R, G, B], axis=-1)
    rgb = np.clip(rgb, 0.0, 1.0)
    H, W = R.shape
    extent_um = (0.0, W * contract.pixel_size_um,
                 0.0, H * contract.pixel_size_um)

    ax.imshow(rgb, origin="lower", extent=extent_um, aspect="equal",
              interpolation="nearest", zorder=2)

    # Mandatory scale bar (20 μm).
    x0, x1, y0, y1 = extent_um
    sb_x = x0 + 0.04 * (x1 - x0)
    sb_y = y0 + 0.04 * (y1 - y0)
    ax.plot([sb_x, sb_x + 20], [sb_y, sb_y],
            color="white", lw=2.5, solid_capstyle="butt", zorder=7)
    ax.text(sb_x + 10, sb_y + 1.5, r"20 $\mu$m",
            ha="center", va="bottom", fontsize=6.4, color="white",
            bbox=dict(boxstyle="round,pad=0.14", fc="#333333",
                      ec="none", alpha=0.65), zorder=7)

    # Per-channel histogram strip in the top-right corner.
    hist_x0 = 0.62
    hist_y0 = 0.78
    hist_w = 0.36
    hist_h = 0.18
    # Background pill.
    import matplotlib.patches as mpatches
    ax.add_patch(mpatches.Rectangle(
        (hist_x0 - 0.005, hist_y0 - 0.005), hist_w + 0.01, hist_h + 0.03,
        facecolor="#111111", edgecolor="none", alpha=0.62,
        transform=ax.transAxes, zorder=5,
    ))
    colors = ["#E53935", "#43A047", "#1E88E5"]
    for ci, (arr, label, color) in enumerate(
        zip([R, G, B], contract.channel_labels, colors)
    ):
        bins = np.linspace(0, 1, 24)
        h, _ = np.histogram(arr.ravel(), bins=bins)
        h_norm = h / max(h.max(), 1)
        step_x = hist_x0 + np.linspace(0, hist_w, h_norm.size)
        row_y = hist_y0 + hist_h * (2 - ci) / 3
        step_y = row_y + h_norm * (hist_h / 3.5)
        ax.plot(step_x, step_y, color=color, lw=0.8,
                transform=ax.transAxes, zorder=6)
        ax.text(hist_x0 + 0.004, row_y, label,
                ha="left", va="bottom", fontsize=5.8, color="white",
                transform=ax.transAxes, zorder=7)

    # Per-channel summary: mean intensity.
    means = [float(R.mean()), float(G.mean()), float(B.mean())]
    ax.text(
        0.02, 0.97,
        f"μR={smart_fmt(means[0])}  μG={smart_fmt(means[1])}  "
        f"μB={smart_fmt(means[2])}",
        transform=ax.transAxes, ha="left", va="top",
        fontsize=6.2, color="white",
        bbox=dict(boxstyle="round,pad=0.18", fc="#111111",
                  ec="none", alpha=0.55),
        zorder=7,
    )

    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    return ax
