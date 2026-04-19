"""Two-photon z-stack depth projection — color-by-depth MIP-style collapse."""

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


class DepthProjInput(RecipeContract):
    z_stack: list[list[list[float]]] = Field(
        ..., description="list of 2D slices (z, y, x), intensity 0-1",
    )
    z_step_um: float = 2.0
    pixel_size_um: float = 0.6
    title: str = "Two-photon MIP · depth-coded"


def _demo() -> DepthProjInput:
    rng = np.random.default_rng(463)
    H, W, Z = 80, 100, 24
    stack = np.zeros((Z, H, W), dtype=float)
    # Seed a few "blobs" at random depths.
    for _ in range(30):
        z = int(rng.integers(2, Z - 2))
        y = int(rng.integers(10, H - 10))
        x = int(rng.integers(10, W - 10))
        r = rng.uniform(2.0, 6.0)
        yy, xx = np.mgrid[:H, :W]
        blob = np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * r ** 2))
        stack[z] += blob * rng.uniform(0.4, 1.0)
    stack += rng.normal(0, 0.01, stack.shape)
    stack = np.clip(stack, 0, None)
    return DepthProjInput(
        z_stack=stack.tolist(),
        z_step_um=2.0,
        pixel_size_um=0.6,
    )


_META = RecipeMetadata(
    name="two_photon_depth_projection",
    modality="intravital_imaging",
    family=RecipeFamily.heatmap,
    answers_question="Where are fluorescent objects distributed in 3D across a two-photon z-stack, encoded by depth?",
    required_fields=("z_stack",),
    optional_fields=("z_step_um", "pixel_size_um", "title"),
    file_format_hints=("tif", "npz"),
    alternatives_in_modality=("cell_track_trajectory_field",),
)


@register_recipe(metadata=_META, contract=DepthProjInput, demo_contract=_demo)
def render(contract: DepthProjInput, ax=None, **_):
    import matplotlib as mpl

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.6))
    AESTHETIC.apply_to_ax(ax)

    stack = np.array(contract.z_stack, dtype=float)
    Z, H, W = stack.shape
    cmap = mpl.colormaps["viridis"]

    # Depth-weighted projection: for each pixel, colour by z of max intensity.
    argmax_z = np.argmax(stack, axis=0)
    max_int = stack.max(axis=0)
    max_int_norm = max_int / max(max_int.max(), 1e-9)
    depth_norm = argmax_z / max(Z - 1, 1)
    rgba = cmap(depth_norm)
    rgba[..., 3] = np.clip(max_int_norm * 1.1, 0.0, 1.0)

    extent = (0, W * contract.pixel_size_um, 0, H * contract.pixel_size_um)
    ax.imshow(rgba, origin="lower", extent=extent,
              aspect="equal", interpolation="bilinear")

    # Scale bar.
    sb_x, sb_y = extent[1] * 0.05, extent[3] * 0.06
    sb_len = 10.0
    ax.plot([sb_x, sb_x + sb_len], [sb_y, sb_y],
            color="white", lw=3.0, solid_capstyle="butt", zorder=6)
    ax.text(sb_x + sb_len / 2, sb_y + 1, r"10 $\mu$m",
            ha="center", va="bottom", fontsize=6.2, color="white",
            bbox=dict(boxstyle="round,pad=0.14", fc="#333333",
                      ec="none", alpha=0.7))

    # Depth colorbar proxy.
    sm = mpl.cm.ScalarMappable(norm=mpl.colors.Normalize(
        vmin=0, vmax=(Z - 1) * contract.z_step_um), cmap=cmap)
    cbar = ax.figure.colorbar(sm, ax=ax, fraction=0.045, pad=0.04)
    cbar.set_label(r"depth ($\mu$m)", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)

    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_title(
        f"{contract.title}  ·  {Z} slices, $\\Delta z$ = {smart_fmt(contract.z_step_um)} $\\mu$m",
        fontsize=8.4, pad=4,
    )
    return ax
