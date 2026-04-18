"""2D parameter scan heatmap + overlay contour of an outcome threshold."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    add_halo_label,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class ParameterScan2DInput(RecipeContract):
    x_name: str
    y_name: str
    x_grid: list[float]
    y_grid: list[float]
    z: list[list[float]] = Field(..., description="z[j][i] = output at (x_grid[i], y_grid[j])")
    threshold: float | None = None
    output_label: str = "output"
    log_x: bool = False
    log_y: bool = False


def _demo() -> ParameterScan2DInput:
    x = np.linspace(-2, 2, 40)
    y = np.linspace(-2, 2, 40)
    X, Y = np.meshgrid(x, y)
    Z = np.exp(-(X**2 + Y**2) / 1.8) * (1 + 0.5 * np.sin(3 * X)) + 0.1 * Y
    return ParameterScan2DInput(
        x_name="log k_on",
        y_name="log Km",
        x_grid=x.tolist(),
        y_grid=y.tolist(),
        z=Z.tolist(),
        threshold=0.5,
        output_label="steady-state gain",
    )


_META = RecipeMetadata(
    name="parameter_scan_2d_contour",
    modality="sensitivity_analysis",
    family=RecipeFamily.contour,
    answers_question="How does the output depend on two parameters jointly, and where is a threshold crossed?",
    required_fields=("x_name", "y_name", "x_grid", "y_grid", "z"),
    optional_fields=("threshold", "output_label", "log_x", "log_y"),
    file_format_hints=("npz", "parquet", "pickle"),
    alternatives_in_modality=("fast_subspace_detection", "pi_group_rank_plot"),
)


@register_recipe(metadata=_META, contract=ParameterScan2DInput, demo_contract=_demo)
def render(contract: ParameterScan2DInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.4, 3.8))
    AESTHETIC.apply_to_ax(ax)
    X, Y = np.meshgrid(contract.x_grid, contract.y_grid)
    Z = np.array(contract.z)
    im = ax.pcolormesh(X, Y, Z, cmap=AESTHETIC.continuous_cmap, shading="auto")
    cs = ax.contour(X, Y, Z, levels=8, colors="white", linewidths=0.5, alpha=0.6)
    ax.clabel(cs, inline=True, fontsize=6.4, fmt=lambda v: smart_fmt(v),
              inline_spacing=4)

    if contract.threshold is not None:
        thresh_cs = ax.contour(
            X, Y, Z,
            levels=[contract.threshold],
            colors="#D32F2F",
            linewidths=2.0,
        )
        try:
            # Attach a halo'd label near the first contour segment.
            paths = thresh_cs.collections[0].get_paths()
            if paths:
                verts = paths[0].vertices
                midx, midy = verts[len(verts) // 2]
                add_halo_label(
                    ax,
                    midx,
                    midy,
                    f"z = {smart_fmt(contract.threshold)}",
                    color="#D32F2F",
                    fontsize=7.0,
                    fontweight="bold",
                    halo_width=2.6,
                )
        except (AttributeError, IndexError):
            pass

    # Max-point marker.
    j_max, i_max = np.unravel_index(np.argmax(Z), Z.shape)
    x_max = contract.x_grid[i_max]
    y_max = contract.y_grid[j_max]
    palette = get_palette(AESTHETIC.primary_palette)
    ax.scatter([x_max], [y_max], s=80, color=palette[1], edgecolor="white",
               linewidth=1.2, zorder=6, marker="*")
    add_halo_label(
        ax,
        x_max,
        y_max,
        f"max = {smart_fmt(float(Z.max()))}",
        color=palette[1],
        fontsize=7.0,
        fontweight="bold",
        halo_width=2.6,
        ha="left",
        va="bottom",
    )

    if contract.log_x:
        ax.set_xscale("log")
    if contract.log_y:
        ax.set_yscale("log")
    ax.set_xlabel(contract.x_name)
    ax.set_ylabel(contract.y_name)
    ax.set_title(f"{contract.output_label} across ({contract.x_name}, {contract.y_name})",
                 fontsize=8.4, fontweight="bold")
    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.042, pad=0.04)
    cbar.set_label(contract.output_label, fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.6)
    return ax
