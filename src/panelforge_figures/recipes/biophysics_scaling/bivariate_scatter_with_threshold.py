"""Bivariate scatter with threshold — two continuous measurements per cell,
stratified by group, optional reference line and per-group linear fit.

Covers z-span vs protrusion-width, standoff vs extent, and similar
per-cell bivariate views.
"""

from __future__ import annotations

from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class BivariateScatterInput(RecipeContract):
    x_by_cell: dict[str, float] = Field(description="cell_id → x value")
    y_by_cell: dict[str, float] = Field(description="cell_id → y value")
    group_by_cell: dict[str, str] = Field(description="cell_id → group label")
    x_label: str = "x"
    y_label: str = "y"
    title: str = "Bivariate scatter"
    threshold_y: float | None = Field(default=None, description="Optional horizontal reference")
    threshold_label: str = "threshold"
    show_correlation: bool = True
    show_fit: bool = True


def _demo() -> BivariateScatterInput:
    import random
    rng = random.Random(42)
    x = {f"c{i}": rng.uniform(0.5, 4.0) for i in range(20)}
    y = {k: 0.5 / (v + 0.5) + rng.gauss(0, 0.05) for k, v in x.items()}
    g = {k: "WT" if i < 7 else "LI" for i, k in enumerate(x)}
    return BivariateScatterInput(
        x_by_cell=x, y_by_cell=y, group_by_cell=g,
        x_label="protrusion width (μm)", y_label="MT z-span (μm)",
        title="z-span vs protrusion width",
        threshold_y=1.5, threshold_label="L_crit ≈ 1.5 μm",
    )


_META = RecipeMetadata(
    name="bivariate_scatter_with_threshold",
    modality="biophysics_scaling",
    family=RecipeFamily.scatter_collapse,
    answers_question="How do two per-cell measurements covary, stratified by group?",
    required_fields=("x_by_cell", "y_by_cell", "group_by_cell"),
    optional_fields=("x_label", "y_label", "title", "threshold_y",
                     "threshold_label", "show_correlation", "show_fit"),
    file_format_hints=("csv", "json"),
    alternatives_in_modality=(
        "shared_manifold_scatter_with_residuals",
        "z_span_vs_width_with_euler_threshold",
    ),
)


@register_recipe(metadata=_META, contract=BivariateScatterInput, demo_contract=_demo)
def render(contract: BivariateScatterInput, ax=None, **_):
    import matplotlib.pyplot as plt
    import numpy as np
    from scipy import stats

    if ax is None:
        _, ax = plt.subplots(figsize=(7, 5.5))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    # Group cells
    cells = list(contract.x_by_cell.keys())
    groups = sorted(set(contract.group_by_cell.get(c, "?") for c in cells))
    for i, g in enumerate(groups):
        sel = [c for c in cells if contract.group_by_cell.get(c) == g]
        xs = np.array([contract.x_by_cell[c] for c in sel], dtype=float)
        ys = np.array([contract.y_by_cell[c] for c in sel], dtype=float)
        m = np.isfinite(xs) & np.isfinite(ys)
        xs, ys = xs[m], ys[m]
        if len(xs) == 0:
            continue
        color = palette[i]
        ax.scatter(xs, ys, s=60, color=color, edgecolor="white",
                   linewidth=0.8, alpha=0.85, label=g, zorder=3)

    # Threshold
    if contract.threshold_y is not None:
        ax.axhline(contract.threshold_y, ls=":", color="#777", lw=1.0,
                   label=contract.threshold_label, zorder=2)

    # Overall fit + correlation
    all_x = np.array([contract.x_by_cell[c] for c in cells], dtype=float)
    all_y = np.array([contract.y_by_cell[c] for c in cells], dtype=float)
    m = np.isfinite(all_x) & np.isfinite(all_y)
    if m.sum() >= 5:
        if contract.show_fit:
            slope, intercept = np.polyfit(all_x[m], all_y[m], 1)
            xs_fit = np.linspace(all_x[m].min(), all_x[m].max(), 50)
            ax.plot(xs_fit, slope * xs_fit + intercept,
                    color="#555", lw=1.2, alpha=0.55, zorder=1)
        if contract.show_correlation:
            r, p = stats.pearsonr(all_x[m], all_y[m])
            ax.text(0.04, 0.94, f"r={r:.2f}, p={p:.3g}",
                    transform=ax.transAxes, fontsize=9.0,
                    bbox=dict(boxstyle="round,pad=0.25", fc="#fff", ec="#ccc"),
                    zorder=10)

    ax.set_xlabel(contract.x_label, fontsize=9.6)
    ax.set_ylabel(contract.y_label, fontsize=9.6)
    ax.set_title(contract.title, fontsize=9.6, color="#2c3e50", pad=6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=9.0, frameon=False, loc="upper right")
    return ax
