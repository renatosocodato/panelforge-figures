"""Branch-angle distribution — stacked KDE ridges per condition with reference."""

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


class BranchAngleInput(RecipeContract):
    angles_deg_by_condition: dict[str, list[float]] = Field(
        ..., description="mother→daughter branch angles (deg) per condition"
    )
    reference_angle_deg: float | None = Field(
        70.0, description="reference angle (e.g. 70° for Arp2/3)"
    )
    title: str = "Branch-angle distribution"


def _demo() -> BranchAngleInput:
    rng = np.random.default_rng(721)
    angles = {
        "control": np.clip(rng.normal(70, 12, 320), 0, 180).tolist(),
        "mutant":  np.clip(rng.normal(52, 18, 320), 0, 180).tolist(),
        "rescue":  np.clip(rng.normal(68, 14, 320), 0, 180).tolist(),
    }
    return BranchAngleInput(
        angles_deg_by_condition=angles,
        reference_angle_deg=70.0,
    )


_META = RecipeMetadata(
    name="branch_angle_distribution",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.ridge_by_group,
    answers_question=(
        "What is the distribution of angles between mother and daughter "
        "branches, by condition, relative to the 70° Arp2/3 reference?"
    ),
    required_fields=("angles_deg_by_condition",),
    optional_fields=("reference_angle_deg", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("filament_orientation_histogram",),
)


def _kde_1d(x: np.ndarray, grid: np.ndarray, bw: float) -> np.ndarray:
    if x.size == 0:
        return np.zeros_like(grid)
    z = (grid[:, None] - x[None, :]) / bw
    K = np.exp(-0.5 * z ** 2) / (bw * np.sqrt(2 * np.pi))
    return K.mean(axis=1)


@register_recipe(
    metadata=_META,
    contract=BranchAngleInput,
    demo_contract=_demo,
)
def render(contract: BranchAngleInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.6))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    conditions = list(contract.angles_deg_by_condition.keys())
    grid = np.linspace(0, 180, 200)
    all_vals = np.concatenate([
        np.asarray(contract.angles_deg_by_condition[c], float)
        for c in conditions
    ])
    if all_vals.size == 0:
        return ax
    bw = max(2.5, float(np.std(all_vals)) * 0.25)
    ridge_height = 1.0

    # Bottom-to-top: first condition at top, last at bottom (stacked).
    for i, name in enumerate(conditions[::-1]):
        vals = np.asarray(contract.angles_deg_by_condition[name], float)
        if vals.size == 0:
            continue
        d = _kde_1d(vals, grid, bw)
        d_norm = d / max(d.max(), 1e-9)
        color = palette[i % len(palette.colors)]
        offset = i
        ax.fill_between(grid, offset, offset + d_norm * ridge_height * 0.9,
                        color=color, alpha=0.55, linewidth=0, zorder=2)
        ax.plot(grid, offset + d_norm * ridge_height * 0.9,
                color=color, lw=1.0, zorder=3)
        ax.text(-4.0, offset + 0.3, name, ha="right", va="center",
                fontsize=6.8, color="#333333")
        med = float(np.median(vals))
        ax.axvline(med, ymin=offset / max(len(conditions), 1),
                   ymax=(offset + 0.9) / max(len(conditions), 1),
                   color=color, lw=0.9, ls="--", zorder=4)
        ax.text(med + 1.5, offset + 0.70,
                f"med {smart_fmt(med)}°",
                ha="left", va="bottom", fontsize=5.8, color="#333333",
                bbox=dict(boxstyle="round,pad=0.10", fc="white",
                          ec="none", alpha=0.85))

    # Reference angle (e.g. Arp2/3 70°).
    if contract.reference_angle_deg is not None:
        ref = float(contract.reference_angle_deg)
        ax.axvline(ref, color="#111111", lw=0.9, ls=":", zorder=5,
                   label=f"reference {smart_fmt(ref)}°")

    ax.set_xlim(0, 180)
    ax.set_xticks([0, 45, 70, 90, 135, 180])
    ax.set_xlabel("branch angle (deg)")
    ax.set_yticks([])
    ax.set_ylim(-0.2, len(conditions) + 0.1)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    if contract.reference_angle_deg is not None:
        ax.legend(fontsize=6.6, frameon=False, loc="upper right",
                  handlelength=1.4)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
