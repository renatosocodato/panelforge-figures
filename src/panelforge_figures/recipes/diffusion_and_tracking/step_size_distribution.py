"""Step-size distribution — per-condition KDE of instantaneous step sizes."""

from __future__ import annotations

import numpy as np
from pydantic import Field
from scipy.stats import gaussian_kde

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class StepSizeInput(RecipeContract):
    steps_by_condition: dict[str, list[float]] = Field(
        ..., description="condition → list of step sizes (μm)"
    )
    title: str = "Step-size distribution"


def _demo() -> StepSizeInput:
    rng = np.random.default_rng(367)
    return StepSizeInput(
        steps_by_condition={
            "free":       rng.rayleigh(0.25, 2500).tolist(),
            "confined":   rng.rayleigh(0.10, 2500).tolist(),
            "directed":   rng.rayleigh(0.45, 2500).tolist(),
        },
    )


_META = RecipeMetadata(
    name="step_size_distribution",
    modality="diffusion_and_tracking",
    family=RecipeFamily.ridge_by_group,
    answers_question="How do step-size distributions compare across conditions — are there confinement or directed-motion signatures?",
    required_fields=("steps_by_condition",),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("msd_by_condition",),
)


@register_recipe(metadata=_META, contract=StepSizeInput, demo_contract=_demo)
def render(contract: StepSizeInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    conditions = list(contract.steps_by_condition.keys())
    all_vals = np.concatenate([
        np.array(contract.steps_by_condition[c], float)
        for c in conditions
    ])
    xg = np.linspace(0, all_vals.max() * 1.05, 240)

    kdes = {c: gaussian_kde(np.array(contract.steps_by_condition[c], float))
            for c in conditions}
    max_d = max(k(xg).max() for k in kdes.values())

    y_step = 1.0
    for i, c in enumerate(conditions[::-1]):
        color = palette[(len(conditions) - 1 - i) % len(palette.colors)]
        dens = kdes[c](xg)
        dens_s = (dens / max_d) * 0.85 * y_step
        y_base = i * y_step
        ax.fill_between(xg, y_base, y_base + dens_s, color=color,
                        alpha=0.55, linewidth=0, zorder=3)
        ax.plot(xg, y_base + dens_s, color=color, lw=0.8, zorder=4)

        vals = np.array(contract.steps_by_condition[c], float)
        ax.text(xg[0], y_base + 0.45 * y_step, c,
                ha="left", va="center", fontsize=7.0, color="#222222")
        ax.text(xg[-1], y_base + 0.1,
                f"med {smart_fmt(float(np.median(vals)))} μm",
                ha="right", va="center", fontsize=6.2, color=color)

    ax.set_xlim(0, xg.max())
    ax.set_ylim(-0.3, len(conditions) - 0.1)
    ax.set_yticks([])
    ax.set_xlabel("step size (μm)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    for s in ("left",):
        ax.spines[s].set_visible(False)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
