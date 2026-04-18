"""Paracrine coupling-length map — spatial autocorrelation of redox ratio."""

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


class ParacrineLengthInput(RecipeContract):
    x_um: list[float]
    y_um: list[float]
    ratio_field: list[list[float]] = Field(
        ..., description="ratio[j][i] on (x_um[i], y_um[j])"
    )
    coupling_length_um: float | None = None
    title: str = "Paracrine coupling length"


def _demo() -> ParacrineLengthInput:
    rng = np.random.default_rng(139)
    x = np.linspace(0, 200, 60)
    y = np.linspace(0, 200, 60)
    X, Y = np.meshgrid(x, y)
    # Ratio field = sum of sources with Gaussian decay; coupling length ~ 20 μm.
    field = np.zeros_like(X)
    for _ in range(6):
        cx = rng.uniform(30, 170)
        cy = rng.uniform(30, 170)
        amp = rng.uniform(0.2, 0.6)
        r2 = (X - cx) ** 2 + (Y - cy) ** 2
        field += amp * np.exp(-r2 / (2 * 20 ** 2))
    # Baseline near 1.
    field = 1.0 + 0.6 * (field - field.mean())
    # Small noise.
    field += rng.normal(0, 0.02, field.shape)
    return ParacrineLengthInput(
        x_um=x.tolist(), y_um=y.tolist(),
        ratio_field=field.tolist(),
        coupling_length_um=20.0,
    )


_META = RecipeMetadata(
    name="paracrine_coupling_length_map",
    modality="redox_imaging",
    family=RecipeFamily.heatmap,
    answers_question="What is the spatial field of redox ratio across the imaging area, and over what length scale are neighbors coupled?",
    required_fields=("x_um", "y_um", "ratio_field"),
    optional_fields=("coupling_length_um", "title"),
    file_format_hints=("npz", "tif", "pickle"),
    alternatives_in_modality=("bistability_hysteresis_loop",),
)


@register_recipe(metadata=_META, contract=ParacrineLengthInput, demo_contract=_demo)
def render(contract: ParacrineLengthInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.6, 3.6))
    AESTHETIC.apply_to_ax(ax)

    X, Y = np.meshgrid(contract.x_um, contract.y_um)
    F = np.array(contract.ratio_field, dtype=float)
    # Center colormap at ratio-neutral = 1.
    vmax = max(abs(F.max() - 1.0), abs(F.min() - 1.0))
    im = ax.imshow(
        F, origin="lower", cmap=AESTHETIC.ratio_cmap or "RdBu_r",
        extent=(contract.x_um[0], contract.x_um[-1],
                contract.y_um[0], contract.y_um[-1]),
        vmin=1 - vmax, vmax=1 + vmax,
        aspect="equal", interpolation="nearest",
    )

    # Coupling-length circle overlay.
    if contract.coupling_length_um is not None:
        cx = (contract.x_um[0] + contract.x_um[-1]) / 2
        cy = (contract.y_um[0] + contract.y_um[-1]) / 2
        from matplotlib.patches import Circle
        ax.add_patch(Circle(
            (cx, cy), contract.coupling_length_um,
            facecolor="none", edgecolor="white", linewidth=1.4,
            linestyle="--", zorder=5,
        ))
        ax.text(cx, cy - contract.coupling_length_um - 4,
                rf"$\lambda_c$ = {smart_fmt(contract.coupling_length_um)} μm",
                ha="center", va="top", fontsize=6.8, color="white",
                bbox=dict(boxstyle="round,pad=0.18", fc="#333333",
                          ec="none", alpha=0.7),
                zorder=6)

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("redox ratio", fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    # Mandatory scale bar (10 μm in x-data coords; placed at lower-left axes).
    x_sb = contract.x_um[0] + 0.05 * (contract.x_um[-1] - contract.x_um[0])
    y_sb = contract.y_um[0] + 0.05 * (contract.y_um[-1] - contract.y_um[0])
    ax.plot([x_sb, x_sb + 20], [y_sb, y_sb],
            color="white", lw=2.5, solid_capstyle="butt", zorder=7)
    ax.text(x_sb + 10, y_sb + 3, "20 μm",
            ha="center", va="bottom", fontsize=6.4, color="white",
            bbox=dict(boxstyle="round,pad=0.14", fc="#333333",
                      ec="none", alpha=0.65))

    ax.set_xlabel("x (μm)")
    ax.set_ylabel("y (μm)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    return ax
