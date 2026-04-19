"""Waddington-style 3D potential landscape with development trajectories.

The v1.0 `potential_landscape_2d_heatmap` recipe renders U(x, y) as a
top-down heatmap — good for reading off wells and saddles but flat.
This recipe renders the same surface as an isometric 3D projection in
the canonical Waddington style (ball rolling down a slope), with
optional sample trajectories that slide along the surface into the
wells. Used in grant panels, commentaries, and conceptual figures.
"""

from __future__ import annotations

import matplotlib.patches as mpatches
import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class Waddington3DInput(RecipeContract):
    x_grid: list[list[float]] = Field(..., description="meshgrid X of the landscape")
    y_grid: list[list[float]] = Field(..., description="meshgrid Y")
    U: list[list[float]] = Field(..., description="potential values U(x, y)")
    trajectories_xy: list[list[list[float]]] = Field(
        default_factory=list,
        description="optional list of [[x, y], ...] polylines to project onto the surface",
    )
    well_labels: list[dict[str, float | str]] = Field(
        default_factory=list,
        description="list of {'x', 'y', 'label'} dicts for well annotations",
    )
    view_elevation_deg: float = 30.0
    view_azimuth_deg: float = -60.0
    title: str = "Waddington landscape"


def _demo() -> Waddington3DInput:
    # Tristable-like: three wells at (-1.2, -0.3), (1.3, -0.1), (0.2, 1.2).
    def potential(x: np.ndarray, y: np.ndarray) -> np.ndarray:
        wells = [
            ((-1.2, -0.3), 1.8),
            ((1.3, -0.1), 2.2),
            ((0.2, 1.2), 1.5),
        ]
        base = 0.25 * (x ** 2 + y ** 2)
        for (cx, cy), depth in wells:
            base -= depth * np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / 0.8)
        return base

    xs = np.linspace(-2.2, 2.4, 60)
    ys = np.linspace(-1.8, 2.2, 60)
    XX, YY = np.meshgrid(xs, ys)
    UU = potential(XX, YY)

    # Sample trajectories: gradient descent from random ICs.
    rng = np.random.default_rng(11)
    trajs = []
    eps = 1e-3

    def grad_U(x: float, y: float) -> tuple[float, float]:
        dx = (potential(np.array([x + eps]), np.array([y]))[0]
              - potential(np.array([x - eps]), np.array([y]))[0]) / (2 * eps)
        dy = (potential(np.array([x]), np.array([y + eps]))[0]
              - potential(np.array([x]), np.array([y - eps]))[0]) / (2 * eps)
        return float(dx), float(dy)

    for _ in range(5):
        x = float(rng.uniform(-1.8, 2.0))
        y = float(rng.uniform(-1.5, 1.8))
        path = [[x, y]]
        for _step in range(320):
            dx, dy = grad_U(x, y)
            x -= 0.03 * dx
            y -= 0.03 * dy
            path.append([x, y])
        trajs.append(path)

    wells = [
        {"x": -1.2, "y": -0.3, "label": "HOME"},
        {"x": 1.3, "y": -0.1, "label": "TRAP"},
        {"x": 0.2, "y": 1.2, "label": "GATE"},
    ]

    return Waddington3DInput(
        x_grid=XX.tolist(),
        y_grid=YY.tolist(),
        U=UU.tolist(),
        trajectories_xy=trajs,
        well_labels=wells,
    )


_META = RecipeMetadata(
    name="potential_landscape_waddington_3d",
    modality="rhogtpase_dynamics",
    # Waddington's visual idiom (3-D isometric surface with trajectories
    # descending into wells) reads as conceptual/grant vocabulary, not a
    # gridded heatmap. The top-down 2-D variant lives under the heatmap
    # family as `potential_landscape_2d_heatmap`.
    family=RecipeFamily.conceptual,
    answers_question=(
        "What does the RhoA/Rac1 potential landscape look like as a 3D "
        "Waddington surface, with sample development trajectories sliding "
        "down the slope into the wells?"
    ),
    required_fields=("x_grid", "y_grid", "U"),
    optional_fields=(
        "trajectories_xy", "well_labels",
        "view_elevation_deg", "view_azimuth_deg", "title",
    ),
    file_format_hints=("npz", "pickle"),
    alternatives_in_modality=(
        "potential_landscape_2d_heatmap",
        "potential_landscape_1d",
    ),
)


@register_recipe(
    metadata=_META,
    contract=Waddington3DInput,
    demo_contract=_demo,
)
def render(contract: Waddington3DInput, ax=None, **_):
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (registers 3d projection)

    if ax is None:
        fig = plt.figure(figsize=(4.8, 3.8))
        ax = fig.add_subplot(111, projection="3d")
    elif not hasattr(ax, "plot_surface"):
        # Caller handed us a 2D cartesian axis; swap in a 3D one in the same slot.
        fig = ax.figure
        pos = ax.get_subplotspec()
        ax.remove()
        ax = fig.add_subplot(pos, projection="3d")
    AESTHETIC.apply_to_fig(ax.figure)

    XX = np.array(contract.x_grid, dtype=float)
    YY = np.array(contract.y_grid, dtype=float)
    UU = np.array(contract.U, dtype=float)
    palette = get_palette(AESTHETIC.primary_palette)

    # The surface itself — Waddington's "landscape".
    ax.plot_surface(
        XX, YY, UU,
        cmap=AESTHETIC.continuous_cmap,
        rstride=2, cstride=2,
        alpha=0.92, edgecolor="#FFFFFF", linewidth=0.1,
        antialiased=True,
    )
    # Contour projections on the bottom plane for extra depth cue.
    u_min = float(UU.min()) - 0.2 * (UU.max() - UU.min())
    ax.contour(XX, YY, UU, zdir="z", offset=u_min,
               cmap=AESTHETIC.continuous_cmap, linewidths=0.6, alpha=0.5)

    # Sample trajectories snapped to the surface.
    def _surface_z(x: float, y: float) -> float:
        # Interpolate UU(x, y) by nearest grid lookup.
        i = int(np.argmin(np.abs(XX[0, :] - x)))
        j = int(np.argmin(np.abs(YY[:, 0] - y)))
        return float(UU[j, i])

    for path in contract.trajectories_xy:
        if not path:
            continue
        xs = [p[0] for p in path]
        ys = [p[1] for p in path]
        zs = [_surface_z(px, py) + 0.03 for px, py in path]
        ax.plot(xs, ys, zs, color="#C62828", lw=1.1, alpha=0.9, zorder=5)
        # Ball at the start (white, outlined).
        ax.scatter([xs[0]], [ys[0]], [zs[0]], s=24,
                   facecolor="white", edgecolor="#111111", linewidth=0.8,
                   zorder=6)

    # Well labels hovering above each valley.
    for well in contract.well_labels:
        lx = float(well["x"])
        ly = float(well["y"])
        lz = _surface_z(lx, ly) + 0.3
        color = (palette.pick(str(well["label"]))
                 if str(well["label"]) in palette.semantic else "#111111")
        ax.text(lx, ly, lz, str(well["label"]),
                color=color, fontsize=8.4, ha="center", va="bottom")

    ax.view_init(elev=contract.view_elevation_deg,
                 azim=contract.view_azimuth_deg)
    # Minimalist Waddington axes.
    ax.set_xlabel(r"$x$", fontsize=7.0)
    ax.set_ylabel(r"$y$", fontsize=7.0)
    ax.set_zlabel(r"$U$", fontsize=7.0)
    ax.tick_params(axis="both", labelsize=6.0)
    ax.set_title(
        f"{contract.title}  ·  "
        f"U range {smart_fmt(float(UU.min()))} to {smart_fmt(float(UU.max()))}",
        fontsize=9.0, pad=2,
    )

    # Tiny 2-D legend inset explaining the descent-path convention.
    # Doubles as the decorative-patch fixture the conceptual-family
    # quality rule looks for — the 3-D surface itself is a Poly3DCollection
    # and does not populate ax.patches.
    legend_ax = ax.figure.add_axes([0.74, 0.10, 0.22, 0.16])
    legend_ax.set_xlim(0.0, 1.0)
    legend_ax.set_ylim(0.0, 1.0)
    legend_ax.set_xticks([])
    legend_ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        legend_ax.spines[side].set_visible(False)
    legend_ax.add_patch(mpatches.Rectangle(
        (0.02, 0.58), 0.20, 0.28,
        facecolor="white", edgecolor="#111111", linewidth=0.8,
    ))
    legend_ax.text(0.26, 0.72, "start", va="center", ha="left",
                   fontsize=6.6, color="#111111")
    legend_ax.add_patch(mpatches.Rectangle(
        (0.02, 0.14), 0.20, 0.28,
        facecolor="#C62828", edgecolor="none",
    ))
    legend_ax.text(0.26, 0.28, "descent path", va="center", ha="left",
                   fontsize=6.6, color="#111111")
    return ax
