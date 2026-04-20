"""Spatial redox-state switching-frequency map — per-pixel switching rate.

Across the imaging field, the number of redox-state transitions per
unit time at each (x, y) pixel, rendered as a heatmap with cell
centroids overplotted and sized by their own per-cell switching rate.

Distinct from `paracrine_coupling_length_map` (ratio field, not
switching rate) and `redox_state_transition_diagram` (aggregated rates,
not spatial).
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


class SwitchingMapInput(RecipeContract):
    x_um: list[float] = Field(..., min_length=3)
    y_um: list[float] = Field(..., min_length=3)
    rate_field: list[list[float]] = Field(
        ..., description="rate[j][i] at (x_um[i], y_um[j]) in events/min"
    )
    cell_x_um: list[float] | None = None
    cell_y_um: list[float] | None = None
    cell_rate: list[float] | None = None
    rate_label: str = "switches / min"
    title: str = "Redox-state switching frequency"


def _demo() -> SwitchingMapInput:
    rng = np.random.default_rng(509)
    x = np.linspace(0, 200, 60)
    y = np.linspace(0, 200, 60)
    X, Y = np.meshgrid(x, y)
    field = np.zeros_like(X)
    # A few switching hotspots.
    for _ in range(5):
        cx = rng.uniform(30, 170)
        cy = rng.uniform(30, 170)
        field += rng.uniform(1.5, 4.0) * np.exp(-((X - cx) ** 2 + (Y - cy) ** 2) / (2 * 14 ** 2))
    field = np.clip(field + rng.normal(0.10, 0.06, field.shape), 0, None)
    cells_x = rng.uniform(20, 180, 22).tolist()
    cells_y = rng.uniform(20, 180, 22).tolist()
    # Per-cell rate ~ samples from field at cell centroid.
    cell_rate = []
    for cx, cy in zip(cells_x, cells_y):
        i = int(np.argmin(np.abs(x - cx)))
        j = int(np.argmin(np.abs(y - cy)))
        cell_rate.append(float(max(field[j, i] + rng.normal(0, 0.25), 0)))
    return SwitchingMapInput(
        x_um=x.tolist(), y_um=y.tolist(),
        rate_field=field.tolist(),
        cell_x_um=cells_x, cell_y_um=cells_y,
        cell_rate=cell_rate,
    )


_META = RecipeMetadata(
    name="redox_state_switching_frequency_map",
    modality="redox_imaging",
    family=RecipeFamily.heatmap,
    answers_question=(
        "Across the imaging field, where do cells switch redox state "
        "most frequently?"
    ),
    required_fields=("x_um", "y_um", "rate_field"),
    optional_fields=(
        "cell_x_um", "cell_y_um", "cell_rate", "rate_label", "title",
    ),
    file_format_hints=("npz", "pickle"),
    alternatives_in_modality=(
        "paracrine_coupling_length_map",
        "redox_state_transition_diagram",
    ),
)


@register_recipe(
    metadata=_META,
    contract=SwitchingMapInput,
    demo_contract=_demo,
)
def render(contract: SwitchingMapInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.6, 3.8))
    AESTHETIC.apply_to_ax(ax)

    x = np.asarray(contract.x_um, float)
    y = np.asarray(contract.y_um, float)
    F = np.asarray(contract.rate_field, float)
    vmax = float(F.max())

    im = ax.imshow(
        F, origin="lower", cmap="inferno",
        extent=(x[0], x[-1], y[0], y[-1]),
        vmin=0.0, vmax=max(vmax, 1e-9),
        aspect="equal", interpolation="nearest",
    )

    # Cell centroids (if provided) scaled by their own switching rate.
    if (contract.cell_x_um is not None and contract.cell_y_um is not None):
        cx = np.asarray(contract.cell_x_um, float)
        cy = np.asarray(contract.cell_y_um, float)
        if contract.cell_rate is not None and len(contract.cell_rate) > 0:
            cr = np.asarray(contract.cell_rate, float)
            sizes = 8 + 42 * (cr / max(cr.max(), 1e-9))
        else:
            sizes = np.full(cx.size, 16.0)
        ax.scatter(cx, cy, s=sizes, facecolor="none",
                   edgecolor="white", linewidth=1.0, zorder=6)

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(contract.rate_label, fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    # Mandatory scale bar (20 μm), lower-left in data coords.
    x_sb = x[0] + 0.05 * (x[-1] - x[0])
    y_sb = y[0] + 0.05 * (y[-1] - y[0])
    ax.plot([x_sb, x_sb + 20], [y_sb, y_sb],
            color="white", lw=2.5, solid_capstyle="butt", zorder=7)
    ax.text(x_sb + 10, y_sb + 3, "20 μm",
            ha="center", va="bottom", fontsize=6.4, color="white",
            bbox=dict(boxstyle="round,pad=0.14", fc="#333333",
                      ec="none", alpha=0.65))

    # Top-right stats pill.
    mean_rate = float(F.mean())
    p95 = float(np.quantile(F, 0.95))
    ax.text(
        0.98, 0.97,
        f"mean = {smart_fmt(mean_rate)}\n95%ile = {smart_fmt(p95)}",
        transform=ax.transAxes, ha="right", va="top",
        fontsize=6.4, color="white",
        bbox=dict(boxstyle="round,pad=0.20", fc="#333333",
                  ec="none", alpha=0.70),
        zorder=6,
    )

    ax.set_xlabel("x (μm)")
    ax.set_ylabel("y (μm)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    return ax
