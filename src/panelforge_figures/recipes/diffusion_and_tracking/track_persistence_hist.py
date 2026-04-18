"""Track persistence histogram — per-track persistence-length distribution."""

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


class PersistenceInput(RecipeContract):
    persistence_length_um: list[float] = Field(...)
    by_condition: dict[str, list[float]] | None = None
    title: str = "Track persistence"


def _demo() -> PersistenceInput:
    rng = np.random.default_rng(383)
    return PersistenceInput(
        persistence_length_um=rng.lognormal(np.log(1.2), 0.5, 500).tolist(),
        by_condition={
            "ctrl": rng.lognormal(np.log(0.9), 0.5, 400).tolist(),
            "LPS":  rng.lognormal(np.log(1.8), 0.5, 400).tolist(),
        },
    )


_META = RecipeMetadata(
    name="track_persistence_hist",
    modality="diffusion_and_tracking",
    family=RecipeFamily.ridge_by_group,
    answers_question="How is track persistence-length distributed, and does it shift across conditions?",
    required_fields=("persistence_length_um",),
    optional_fields=("by_condition", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("angle_correlation_decay",),
)


@register_recipe(metadata=_META, contract=PersistenceInput, demo_contract=_demo)
def render(contract: PersistenceInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.6, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    # Overall distribution as density histogram first.
    all_vals = np.array(contract.persistence_length_um, dtype=float)
    hist, edges = np.histogram(all_vals, bins=40, density=True)
    centers = 0.5 * (edges[:-1] + edges[1:])
    ax.fill_between(centers, 0, hist, color="#BBBBBB", alpha=0.4,
                    linewidth=0, zorder=2, label=f"all (N={len(all_vals)})")

    # Per-condition KDE overlays.
    if contract.by_condition is not None:
        from scipy.stats import gaussian_kde
        xg = np.linspace(0, all_vals.max() * 1.05, 250)
        for i, (name, vals) in enumerate(contract.by_condition.items()):
            color = palette[i % len(palette.colors)]
            kde = gaussian_kde(np.array(vals, float))
            ax.plot(xg, kde(xg), color=color, lw=1.3, zorder=3,
                    label=f"{name} (N={len(vals)})")
            ax.fill_between(xg, 0, kde(xg), color=color, alpha=0.10,
                            linewidth=0, zorder=2)

    ax.set_xlabel(r"persistence length ($\mu$m)")
    ax.set_ylabel("density")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.6)

    ax.text(0.99, 0.02,
            f"overall median = {smart_fmt(float(np.median(all_vals)))} μm",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6.2, color="#444444",
            bbox=dict(boxstyle="round,pad=0.18", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
