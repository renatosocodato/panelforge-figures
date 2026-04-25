"""Width x alpha regime phase map — the §6 centerpiece. Heatmap of a
modeled quantity over (protrusion_width_um, alignment_alpha) with
iso-alpha contours, per-group density contours, regime-corner glyphs,
and an optional model-space rescue-zone polygon.

The pack's headline forward-validation panel: it shows where in
(width, alpha) parameter space the genotypes live, where the regime
boundaries sit (iso-alpha contours), and where a model-hypothesised
rescue zone would lie. The rescue zone is rendered with explicit
"model hypothesis" framing so it can never be over-read as observed.

Heatmap family: >=1 imshow / pcolormesh. Satisfied by pcolormesh of
the phase-map values; all overlays draw on top.
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
from ._shared import PhaseMapGrid

_GROUP_COLOURS = {"WT": "#1565C0", "LI": "#C62828",
                  "control": "#1565C0", "treated": "#C62828"}


class WidthAlphaPhaseMapInput(RecipeContract):
    grid: PhaseMapGrid
    rescue_zone_polygon: list[list[float]] | None = Field(
        None,
        description=(
            "model-space hypothesised rescue-zone polygon "
            "(rendered with 'model hypothesis' tag)"
        ),
    )
    iso_alpha_values: list[float] = Field(
        default_factory=lambda: [0.3, 0.5, 0.7],
    )
    cmap: str = "magma"
    title: str = "Width × alpha regime phase map"


def _demo() -> WidthAlphaPhaseMapInput:
    # Width × alpha grid; values = simulated alignment alpha at steady
    # state (so the heatmap and y-axis are in the same units; iso-α
    # contours then sit on simple horizontal-ish surfaces).
    width = np.linspace(0.4, 4.0, 36)
    alpha = np.linspace(0.0, 1.0, 26)
    W, A = np.meshgrid(width, alpha)
    # Modelled steady-state alpha: increases with width, with a small
    # kink near w = 1.0 µm where alpha rolls over more steeply.
    values = (
        0.20 + 0.55 * np.tanh((W - 1.0) / 0.7)
        + 0.05 * np.sin(2 * np.pi * A)
    )

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
    # Optional rescue zone (model-space hypothesis): width range
    # (1.5, 2.0) where LI cells would behave as WT.
    rescue = [
        [1.5, 0.40], [2.0, 0.40],
        [2.0, 0.85], [1.5, 0.85],
        [1.5, 0.40],
    ]
    return WidthAlphaPhaseMapInput(
        grid=PhaseMapGrid(
            x_axis_label="protrusion_width_um",
            y_axis_label="alignment_alpha",
            x_edges=width.tolist(),
            y_edges=alpha.tolist(),
            values=values.tolist(),
            group_density_contours=contours,
            regime_corners=regime_corners,
        ),
        rescue_zone_polygon=rescue,
        iso_alpha_values=[0.3, 0.5, 0.7],
    )


_META = RecipeMetadata(
    name="width_alpha_regime_phase_map",
    modality="biophysics_scaling",
    family=RecipeFamily.heatmap,
    answers_question=(
        "Across (width, alpha) parameter space, where do the "
        "genotypes live, where do regime boundaries sit, and where "
        "would a model-hypothesised rescue zone be?"
    ),
    required_fields=("grid",),
    optional_fields=(
        "rescue_zone_polygon", "iso_alpha_values", "cmap", "title",
    ),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("robustness_neighborhood_phase_corner",),
)


@register_recipe(
    metadata=_META,
    contract=WidthAlphaPhaseMapInput,
    demo_contract=_demo,
)
def render(contract: WidthAlphaPhaseMapInput, ax=None, **_):
    import matplotlib.patches as mpatches
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.0, 4.4))
    AESTHETIC.apply_to_ax(ax)

    grid = contract.grid
    x_edges = np.asarray(grid.x_edges, float)
    y_edges = np.asarray(grid.y_edges, float)
    values = np.asarray(grid.values, float)

    # Phase-map heatmap.
    mesh = ax.pcolormesh(x_edges, y_edges, values,
                         cmap=contract.cmap, shading="auto",
                         alpha=0.85, zorder=1)
    cbar = ax.figure.colorbar(mesh, ax=ax, fraction=0.04, pad=0.03)
    cbar.set_label("simulated alpha (steady state)", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.0)

    # Iso-alpha contours: solid black lines at each requested level.
    # The coord grid uses the cell-CENTER convention (values is
    # rows=alpha-bins x cols=width-bins, sharing the same shape as
    # meshgrid(x_edges, y_edges) when values came from a meshgrid of
    # the original axes).
    Xc, Yc = np.meshgrid(x_edges, y_edges)
    if values.shape == Xc.shape:
        v_lo, v_hi = float(values.min()), float(values.max())
        levels_in_range = sorted(
            v for v in contract.iso_alpha_values
            if v_lo < v < v_hi
        )
        if levels_in_range:
            # Black contours for high contrast against the magma cmap
            # (white was illegible against the light-tan high-value
            # region).
            cs = ax.contour(Xc, Yc, values,
                            levels=levels_in_range,
                            colors="#222222", linewidths=1.2,
                            linestyles="-", zorder=4)
            ax.clabel(cs, inline=True, fontsize=6.4, fmt="%.2f")

    # Group density contours (dashed) and centroid markers.
    if grid.group_density_contours:
        for group, polygon in grid.group_density_contours.items():
            colour = _GROUP_COLOURS.get(group, "#333333")
            poly = np.asarray(polygon, float)
            if poly.ndim != 2:
                continue
            ax.plot(poly[:, 0], poly[:, 1],
                    color=colour, lw=1.2, ls="--", alpha=0.85,
                    zorder=5, label=f"{group} density")
            cx = float(poly[:, 0].mean())
            cy = float(poly[:, 1].mean())
            ax.scatter([cx], [cy], s=42, marker="o",
                       facecolor=colour, edgecolor="white",
                       linewidth=0.6, zorder=6)

    # Regime corners — plus glyph + bracket-style label callouts.
    if grid.regime_corners:
        for label, (cx, cy) in grid.regime_corners.items():
            ax.scatter([cx], [cy], s=80, marker="P",
                       facecolor="#FFFFFF", edgecolor="#222222",
                       linewidth=0.8, zorder=7)
            # Offset label up-and-right for upper corners, up-and-left
            # for lower corners (flip horizontally if x > x_max/2).
            x_mid = (x_edges[0] + x_edges[-1]) / 2
            ha = "left" if cx < x_mid else "right"
            x_text = 8 if cx < x_mid else -8
            ax.annotate(
                label, xy=(cx, cy),
                xytext=(x_text, 8), textcoords="offset points",
                fontsize=6.6, color="#222222", fontweight="bold", ha=ha,
                bbox=dict(boxstyle="round,pad=0.22", fc="white",
                          ec="#BBBBBB", lw=0.4, alpha=0.92),
                zorder=8,
            )

    # Optional rescue zone — model-space hypothesis. Tag pinned at
    # bottom edge of the polygon (inside) so it can't collide with
    # regime-corner labels which sit near corner glyphs further inside.
    if contract.rescue_zone_polygon:
        poly = np.asarray(contract.rescue_zone_polygon, float)
        ax.add_patch(mpatches.Polygon(
            poly, closed=True,
            facecolor="#9E9E9E", alpha=0.18,
            edgecolor="#222222", linewidth=0.8, linestyle="--",
            zorder=3,
        ))
        cx = float(poly[:, 0].mean())
        cy_bot = float(poly[:, 1].min())
        ax.text(
            cx, cy_bot + (poly[:, 1].max() - cy_bot) * 0.06,
            "model hypothesis: rescue zone",
            ha="center", va="bottom", fontsize=6.0,
            color="#444444", style="italic", zorder=4,
            bbox=dict(boxstyle="round,pad=0.22", fc="#FAFAFA",
                      ec="#BBBBBB", lw=0.4, alpha=0.85),
        )

    # Optional robustness neighborhood (drawn last so it sits on top).
    if grid.robustness_neighborhood:
        poly = np.asarray(grid.robustness_neighborhood, float)
        ax.plot(np.append(poly[:, 0], poly[0, 0]),
                np.append(poly[:, 1], poly[0, 1]),
                color="#000000", lw=1.1, ls=":",
                zorder=9, label="robustness ring")

    ax.set_xlabel(grid.x_axis_label.replace("_", " "))
    ax.set_ylabel(grid.y_axis_label.replace("_", " "))
    ax.set_xlim(x_edges.min(), x_edges.max())
    ax.set_ylim(y_edges.min(), y_edges.max())
    # Legend below axes — upper-left collides with the LI density
    # contour and "LI confinement-facing" regime corner.
    ax.legend(fontsize=6.4, frameon=False, loc="upper center",
              bbox_to_anchor=(0.5, -0.10), ncols=3, handlelength=1.2)

    n_iso = len(contract.iso_alpha_values)
    ax.set_title(
        f"{contract.title}  ·  {n_iso} iso-alpha contours  ·  "
        f"alpha range {smart_fmt(float(values.min()))} - "
        f"{smart_fmt(float(values.max()))}",
        fontsize=8.2, pad=4,
    )
    return ax
