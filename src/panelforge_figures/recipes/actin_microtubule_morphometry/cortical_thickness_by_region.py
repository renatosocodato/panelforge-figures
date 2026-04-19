"""Cortical thickness by region — ridge plot of cortex thickness per anatomical region."""

from __future__ import annotations

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


class CortexThicknessInput(RecipeContract):
    regions: list[str] = Field(..., min_length=2)
    thickness_um_by_region: dict[str, list[float]] = Field(...)
    title: str = "Cortical actin thickness"


def _demo() -> CortexThicknessInput:
    rng = np.random.default_rng(497)
    regions = ["leading edge", "mid-lamella", "perinuclear", "uropod"]
    means = [0.45, 0.30, 0.22, 0.36]
    thick = {
        name: rng.gamma(6, mu / 6, 240).tolist()
        for name, mu in zip(regions, means)
    }
    return CortexThicknessInput(
        regions=regions,
        thickness_um_by_region=thick,
    )


_META = RecipeMetadata(
    name="cortical_thickness_by_region",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.ridge_by_group,
    answers_question="How does cortical actin thickness vary across distinct anatomical regions of a cell?",
    required_fields=("regions", "thickness_um_by_region"),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("filament_orientation_histogram",),
)


def _kde_1d(x: np.ndarray, grid: np.ndarray, bw: float) -> np.ndarray:
    """Simple Gaussian KDE on a 1D grid."""
    if x.size == 0:
        return np.zeros_like(grid)
    z = (grid[:, None] - x[None, :]) / bw
    K = np.exp(-0.5 * z * z) / (bw * np.sqrt(2 * np.pi))
    return K.mean(axis=1)


@register_recipe(metadata=_META, contract=CortexThicknessInput, demo_contract=_demo)
def render(contract: CortexThicknessInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    regions = contract.regions
    all_vals = np.concatenate([
        np.array(contract.thickness_um_by_region.get(r, []), float)
        for r in regions
    ])
    if all_vals.size == 0:
        return ax
    grid = np.linspace(max(all_vals.min() * 0.8, 0), all_vals.max() * 1.15, 200)
    bw = max(0.03, np.std(all_vals) * 0.3)
    ridge_height = 1.0

    for i, r in enumerate(regions[::-1]):
        vals = np.array(contract.thickness_um_by_region.get(r, []), float)
        if vals.size == 0:
            continue
        d = _kde_1d(vals, grid, bw)
        d = d / max(d.max(), 1e-9)
        color = palette[i % len(palette.colors)]
        offset = i
        ax.fill_between(grid, offset, offset + d * ridge_height * 0.9,
                        color=color, alpha=0.55, linewidth=0, zorder=2)
        ax.plot(grid, offset + d * ridge_height * 0.9,
                color=color, lw=1.0, zorder=3)
        ax.text(grid[0] - (grid[-1] - grid[0]) * 0.02, offset + 0.3,
                r, ha="right", va="center",
                fontsize=6.8, color="#333333")
        med = float(np.median(vals))
        ax.axvline(med, ymin=offset / len(regions),
                   ymax=(offset + 0.9) / len(regions),
                   color=color, lw=0.9, ls="--", zorder=4)
        ax.text(med, offset + 0.75, smart_fmt(med),
                ha="center", va="bottom", fontsize=5.8, color="#333333",
                bbox=dict(boxstyle="round,pad=0.12", fc="white",
                          ec="none", alpha=0.9))

    ax.set_xlabel(r"cortical thickness ($\mu$m)")
    ax.set_yticks([])
    ax.set_ylim(-0.3, len(regions) + 0.2)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
