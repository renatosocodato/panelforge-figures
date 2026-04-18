"""Marginal-effects ribbon — fitted mean + 95% CI per group over a continuous predictor."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class MarginalEffectsInput(RecipeContract):
    x: list[float] = Field(...)
    groups: dict[str, dict[str, list[float]]] = Field(
        ..., description="group → {mean, lo, hi} arrays aligned to x"
    )
    x_label: str = "predictor"
    y_label: str = "marginal mean"
    title: str = "Marginal effects"


def _demo() -> MarginalEffectsInput:
    x = np.linspace(-2, 2, 40)
    groups: dict[str, dict[str, list[float]]] = {}
    for name, shift, slope in [
        ("F · WT", 0.0, 0.45),
        ("M · WT", -0.15, 0.30),
        ("F · KO", -0.25, 0.15),
        ("M · KO", -0.40, 0.05),
    ]:
        mean = shift + slope * x + 0.05 * np.sin(1.5 * x)
        w = 0.15 + 0.04 * np.abs(x)
        groups[name] = {
            "mean": mean.tolist(),
            "lo": (mean - w).tolist(),
            "hi": (mean + w).tolist(),
        }
    return MarginalEffectsInput(
        x=x.tolist(),
        groups=groups,
        x_label="age (z)",
        y_label="fitted outcome",
        title="Sex × genotype × age marginal effects",
    )


_META = RecipeMetadata(
    name="marginal_effects_ribbon",
    modality="mixed_effects_models",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question="How does the fitted outcome change with a continuous predictor, separately per group?",
    required_fields=("x", "groups"),
    optional_fields=("x_label", "y_label", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("emmeans_contrast_grid", "posterior_predictive_check"),
)


@register_recipe(metadata=_META, contract=MarginalEffectsInput, demo_contract=_demo)
def render(contract: MarginalEffectsInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.4))
    AESTHETIC.apply_to_ax(ax)

    palette = get_palette(AESTHETIC.primary_palette)
    x = np.array(contract.x, dtype=float)

    group_names = list(contract.groups.keys())
    for i, name in enumerate(group_names):
        # Prefer semantic lookup when name matches a palette key.
        key = name.replace(" · ", "_").replace("♀", "F").replace("♂", "M")
        color = (
            palette.pick(key) if key in palette.semantic
            else palette[i]
        )
        g = contract.groups[name]
        mean = np.asarray(g["mean"], float)
        lo = np.asarray(g["lo"], float)
        hi = np.asarray(g["hi"], float)
        ax.fill_between(x, lo, hi, color=color, alpha=0.18,
                        linewidth=0, zorder=2)
        ax.plot(x, mean, color=color, lw=1.2, label=name, zorder=3)

    ax.set_xlabel(contract.x_label)
    ax.set_ylabel(contract.y_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="upper left",
              ncol=2, handlelength=1.6, columnspacing=1.0)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
