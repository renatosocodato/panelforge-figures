"""Robustness-neighborhood phase corner — phase-map heatmap with group
density contours, regime-corner glyphs, and a dashed polygon marking
the perturbation neighborhood. Footer pill reports the fraction of
the neighborhood that preserves the regime split.

The proposal's robustness audit: does the phase-corner regime
classification hold under a local perturbation of the simulation
parameters? If yes, the regime claim is robust; if no, the corner
sits on a regime boundary and the claim needs softening.

Heatmap family: >=1 imshow / pcolormesh. Satisfied by `pcolormesh`
of `PhaseMapGrid.values`; overlays draw on top.
"""

from __future__ import annotations

import numpy as np

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC
from ._shared import PhaseMapGrid

_GROUP_COLOURS = {"WT": "#1565C0", "LI": "#C62828",
                  "control": "#1565C0", "treated": "#C62828"}


class RobustnessNeighborhoodInput(RecipeContract):
    grid: PhaseMapGrid
    centroid_by_group: dict[str, tuple[float, float]] | None = None
    perturbation_budget_units: str = "20 % each axis"
    cmap: str = "viridis"
    title: str = "Robustness neighborhood — phase corner"


def _demo() -> RobustnessNeighborhoodInput:
    # Width × alpha grid, value = "regime-split likelihood" via
    # smooth Gaussian centred on (1.6, 0.7).
    width = np.linspace(0.4, 4.0, 30)
    alpha = np.linspace(0.0, 1.0, 25)
    W, A = np.meshgrid(width, alpha)
    values = np.exp(-((W - 1.6) ** 2) / 1.4 - ((A - 0.7) ** 2) / 0.3)

    # Group density contours (synthetic Gaussian density polygons).
    def _ellipse_polygon(cx: float, cy: float, rx: float, ry: float,
                         n: int = 60) -> list[list[float]]:
        theta = np.linspace(0, 2 * np.pi, n)
        return [[float(cx + rx * np.cos(t)),
                 float(cy + ry * np.sin(t))] for t in theta]

    contours = {
        "WT": _ellipse_polygon(2.0, 0.55, 0.55, 0.12),
        "LI": _ellipse_polygon(0.85, 0.78, 0.40, 0.10),
    }
    regime_corners = {
        "WT buffered": (2.5, 0.55),
        "LI confinement-facing": (0.8, 0.85),
    }
    # Robustness neighborhood: ±20 % around (1.6, 0.7).
    centre = (1.6, 0.7)
    rx = 0.2 * centre[0]
    ry = 0.2 * centre[1]
    robustness = _ellipse_polygon(centre[0], centre[1], rx, ry, n=80)

    return RobustnessNeighborhoodInput(
        grid=PhaseMapGrid(
            x_axis_label="protrusion_width_um",
            y_axis_label="alignment_alpha",
            x_edges=width.tolist(),
            y_edges=alpha.tolist(),
            values=values.tolist(),
            group_density_contours=contours,
            regime_corners=regime_corners,
            robustness_neighborhood=robustness,
        ),
        centroid_by_group={"WT": (2.0, 0.55), "LI": (0.85, 0.78)},
    )


_META = RecipeMetadata(
    name="robustness_neighborhood_phase_corner",
    modality="biophysics_scaling",
    family=RecipeFamily.heatmap,
    answers_question=(
        "Does the regime classification at this phase corner hold "
        "across a local perturbation neighborhood of simulation "
        "parameters?"
    ),
    required_fields=("grid",),
    optional_fields=(
        "centroid_by_group", "perturbation_budget_units",
        "cmap", "title",
    ),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("width_alpha_regime_phase_map",),
)


def _polygon_contains(poly: np.ndarray, pt: tuple[float, float]) -> bool:
    """Ray-casting point-in-polygon test for a closed 2-D polygon."""
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            x_at_y = x0 + (y - y0) * (x1 - x0) / (y1 - y0 + 1e-12)
            if x < x_at_y:
                inside = not inside
    return inside


@register_recipe(
    metadata=_META,
    contract=RobustnessNeighborhoodInput,
    demo_contract=_demo,
)
def render(contract: RobustnessNeighborhoodInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 4.2))
    AESTHETIC.apply_to_ax(ax)

    grid = contract.grid
    x_edges = np.asarray(grid.x_edges, float)
    y_edges = np.asarray(grid.y_edges, float)
    values = np.asarray(grid.values, float)

    # Phase-map heatmap (pcolormesh on the parent ax).
    mesh = ax.pcolormesh(x_edges, y_edges, values,
                         cmap=contract.cmap, shading="auto",
                         alpha=0.85, zorder=1)
    cbar = ax.figure.colorbar(mesh, ax=ax, fraction=0.04, pad=0.03)
    cbar.set_label("regime-split likelihood", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.0)

    # Group density contours (dashed).
    if grid.group_density_contours:
        for group, polygons in grid.group_density_contours.items():
            colour = _GROUP_COLOURS.get(group, "#333333")
            poly = np.asarray(polygons, float)
            if poly.ndim != 2:
                continue
            ax.plot(poly[:, 0], poly[:, 1],
                    color=colour, lw=1.2, ls="--", alpha=0.85,
                    zorder=4, label=f"{group} density")

    # Centroid markers per group.
    if contract.centroid_by_group:
        for group, (cx, cy) in contract.centroid_by_group.items():
            colour = _GROUP_COLOURS.get(group, "#333333")
            ax.scatter([cx], [cy], s=64, marker="o",
                       facecolor=colour, edgecolor="white",
                       linewidth=0.7, zorder=6)

    # Regime corners.
    if grid.regime_corners:
        for label, (cx, cy) in grid.regime_corners.items():
            ax.scatter([cx], [cy], s=80, marker="P",
                       facecolor="#FFFFFF", edgecolor="#222222",
                       linewidth=0.8, zorder=6)
            # Larger offset (12, 12) keeps the white-bg label clear
            # of nearby centroid markers and overlapping density
            # contours.
            ax.annotate(
                label, xy=(cx, cy),
                xytext=(12, 12), textcoords="offset points",
                fontsize=6.6, color="#222222", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.22", fc="white",
                          ec="#BBBBBB", lw=0.4, alpha=0.92),
                zorder=7,
            )

    # Robustness neighborhood polygon (drawn LAST = highest z-order so
    # overlays don't hide it).
    fraction = None
    if grid.robustness_neighborhood:
        poly = np.asarray(grid.robustness_neighborhood, float)
        ax.plot(np.append(poly[:, 0], poly[0, 0]),
                np.append(poly[:, 1], poly[0, 1]),
                color="#000000", lw=1.1, ls=":",
                zorder=8, label="robustness ring")
        # Fraction of neighborhood preserving the regime split: the
        # neighborhood lies on a single side of the value-median if
        # the median value across the neighborhood is consistently
        # above or below the global median.
        sample_n = 80
        rng = np.random.default_rng(0)
        cx = float(poly[:, 0].mean())
        cy = float(poly[:, 1].mean())
        # Sample points uniformly over a bounding box, keep those
        # inside the polygon, and check what side of the global value
        # median they land on.
        x_min, x_max = float(poly[:, 0].min()), float(poly[:, 0].max())
        y_min, y_max = float(poly[:, 1].min()), float(poly[:, 1].max())
        xs = rng.uniform(x_min, x_max, sample_n)
        ys = rng.uniform(y_min, y_max, sample_n)
        inside = np.array([_polygon_contains(poly, (x, y))
                           for x, y in zip(xs, ys)])
        if inside.any():
            v_global = float(np.median(values))
            xs_in = xs[inside]
            ys_in = ys[inside]
            # Look up grid value at each point via nearest-neighbor.
            v_at = np.zeros(xs_in.size)
            for i, (x, y) in enumerate(zip(xs_in, ys_in)):
                ix = int(np.clip(np.searchsorted(x_edges, x) - 1,
                                 0, values.shape[1] - 1))
                iy = int(np.clip(np.searchsorted(y_edges, y) - 1,
                                 0, values.shape[0] - 1))
                v_at[i] = values[iy, ix]
            same_side = ((v_at > v_global).all()
                         or (v_at < v_global).all())
            fraction = float(
                np.mean(np.sign(v_at - v_global)
                        == np.sign(values[
                            int(np.clip(np.searchsorted(y_edges, cy) - 1,
                                        0, values.shape[0] - 1)),
                            int(np.clip(np.searchsorted(x_edges, cx) - 1,
                                        0, values.shape[1] - 1)),
                        ] - v_global))
            )
            _ = same_side

    ax.set_xlabel(grid.x_axis_label.replace("_", " "))
    ax.set_ylabel(grid.y_axis_label.replace("_", " "))
    ax.legend(fontsize=6.4, frameon=False, loc="upper right",
              handlelength=1.2)

    title_bits = [contract.title]
    if fraction is not None:
        title_bits.append(
            f"{smart_fmt(fraction * 100)} % of neighborhood preserves split"
        )
    title_bits.append(
        f"perturbation = {contract.perturbation_budget_units}"
    )
    ax.set_title("  ·  ".join(title_bits), fontsize=8.2, pad=4)
    return ax
