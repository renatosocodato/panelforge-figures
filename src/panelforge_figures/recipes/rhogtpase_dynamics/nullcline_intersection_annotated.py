"""Nullclines in the 2D phase plane — intersections mark fixed points."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    fixed_point_marker,
    get_palette,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class NullclineInput(RecipeContract):
    x_grid: list[float]
    y_grid: list[float]
    fx: list[list[float]] = Field(..., description="f(x,y) values where dx/dt = f")
    gy: list[list[float]] = Field(..., description="g(x,y) values where dy/dt = g")
    fixed_points: list[tuple[float, float, str]] = Field(
        default_factory=list,
        description="list of (x, y, kind) — kind ∈ {stable, unstable, saddle}",
    )
    x_label: str = "x"
    y_label: str = "y"
    title: str = "Nullclines"


def _demo() -> NullclineInput:
    x = np.linspace(-2, 2, 80)
    y = np.linspace(-2, 2, 80)
    X, Y = np.meshgrid(x, y)
    fx = Y - X ** 3 + X           # cubic x-nullcline when fx=0
    gy = -Y + X                   # linear y-nullcline when gy=0
    fps = [
        (-1.3, -1.3, "stable"),
        (0.0, 0.0, "unstable"),
        (1.3, 1.3, "stable"),
    ]
    return NullclineInput(
        x_grid=x.tolist(), y_grid=y.tolist(),
        fx=fx.tolist(), gy=gy.tolist(),
        fixed_points=fps,
    )


_META = RecipeMetadata(
    name="nullcline_intersection_annotated",
    modality="rhogtpase_dynamics",
    family=RecipeFamily.phase_portrait,
    answers_question="Where do the x- and y-nullclines intersect, and what is the stability of each fixed point?",
    required_fields=("x_grid", "y_grid", "fx", "gy"),
    optional_fields=("fixed_points", "x_label", "y_label", "title"),
    file_format_hints=("npz", "pickle"),
    alternatives_in_modality=("phase_portrait_bistable", "phase_portrait_tristable"),
)


@register_recipe(metadata=_META, contract=NullclineInput, demo_contract=_demo)
def render(contract: NullclineInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.6, 3.6))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    X, Y = np.meshgrid(contract.x_grid, contract.y_grid)
    fx = np.array(contract.fx, dtype=float)
    gy = np.array(contract.gy, dtype=float)

    # Quiver (coarse).
    step = max(1, X.shape[0] // 16)
    ax.quiver(X[::step, ::step], Y[::step, ::step],
              fx[::step, ::step], gy[::step, ::step],
              color="#BBBBBB", width=0.003, zorder=2)

    # Nullclines.
    cs_x = ax.contour(X, Y, fx, levels=[0], colors=[palette.pick("HOME")],
                      linewidths=1.3, linestyles="--", zorder=3)
    cs_y = ax.contour(X, Y, gy, levels=[0], colors=[palette.pick("TRAP")],
                      linewidths=1.3, linestyles="--", zorder=3)
    ax.clabel(cs_x, inline=True, fontsize=6.0, fmt=lambda _: "x-null",
              inline_spacing=2)
    ax.clabel(cs_y, inline=True, fontsize=6.0, fmt=lambda _: "y-null",
              inline_spacing=2)

    # Fixed points.
    for (x_fp, y_fp, kind) in contract.fixed_points:
        fixed_point_marker(ax, x_fp, y_fp, kind)

    ax.set_xlabel(contract.x_label)
    ax.set_ylabel(contract.y_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.set_xlim(X.min(), X.max())
    ax.set_ylim(Y.min(), Y.max())

    from matplotlib.lines import Line2D
    proxies = [
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor="black", markeredgecolor="white",
               markersize=6, label="stable"),
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor="white", markeredgecolor="black",
               markersize=6, label="unstable"),
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor="#888888", markeredgecolor="black",
               markersize=6, label="saddle"),
    ]
    ax.legend(handles=proxies, loc="lower right",
              fontsize=6.4, frameon=True, framealpha=0.92,
              edgecolor="#BBBBBB", borderpad=0.4, handlelength=1.0)
    return ax
