"""Baseline characteristics — covariate means across arms with SMD annotation."""

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


class BaselineInput(RecipeContract):
    covariates: list[str] = Field(..., min_length=1)
    arm_names: list[str] = Field(..., min_length=2)
    arm_means: list[list[float]] = Field(
        ..., description="arm_means[arm][cov] standardised mean in [0, 1]",
    )
    smd: list[float] = Field(..., description="standardised mean difference per covariate")
    title: str = "Baseline characteristics"


def _demo() -> BaselineInput:
    covariates = [
        "Age (standardised)", "BMI", "Sex (F fraction)",
        "Smoker fraction", "Hypertension", "Diabetes",
        "Baseline biomarker", "Prior therapy", "Performance status",
    ]
    arms = ["Control", "Intervention"]
    rng = np.random.default_rng(427)
    ctrl = rng.uniform(0.3, 0.7, len(covariates))
    intv = ctrl + rng.normal(0, 0.05, len(covariates))
    intv = np.clip(intv, 0, 1)
    smd = np.abs(intv - ctrl) / 0.25
    return BaselineInput(
        covariates=covariates,
        arm_names=arms,
        arm_means=[ctrl.tolist(), intv.tolist()],
        smd=smd.tolist(),
    )


_META = RecipeMetadata(
    name="baseline_table_visualization",
    modality="clinical_cohort",
    family=RecipeFamily.matrix,
    answers_question="Are the randomized arms balanced on baseline covariates, or does the standardised-mean-difference flag an imbalance?",
    required_fields=("covariates", "arm_names", "arm_means", "smd"),
    optional_fields=("title",),
    file_format_hints=("csv",),
    alternatives_in_modality=("consort_flow_diagram",),
)


@register_recipe(metadata=_META, contract=BaselineInput, demo_contract=_demo)
def render(contract: BaselineInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    covs = contract.covariates
    arms = contract.arm_names
    means = np.array(contract.arm_means, dtype=float)
    smd = np.array(contract.smd, dtype=float)
    y = np.arange(len(covs))[::-1]

    width = 0.38
    for ai, name in enumerate(arms):
        offset = (ai - (len(arms) - 1) / 2) * width
        color = palette[ai % len(palette.colors)]
        ax.barh(y + offset, means[ai], height=width, color=color,
                alpha=0.85, edgecolor="white", linewidth=0.5,
                zorder=3, label=name)

    # SMD markers to the right.
    smd_threshold = 0.1
    xhi = 1.35
    ax.set_xlim(0, xhi)
    for yi, s in zip(y, smd):
        color = "#D32F2F" if s > smd_threshold else "#2E7D32"
        ax.scatter([1.08], [yi], s=34, color=color,
                   edgecolor="white", linewidth=0.7, zorder=4)
        ax.text(1.14, yi, f"SMD={smart_fmt(float(s))}",
                va="center", ha="left", fontsize=6.2, color=color)

    ax.axvline(1.0, color="#999999", lw=0.5, ls=":", zorder=1)
    ax.set_yticks(y)
    ax.set_yticklabels(covs, fontsize=6.8)
    ax.set_xlabel("standardised value (0-1)")
    ax.set_title(
        f"{contract.title}  ·  red SMD > {smd_threshold}",
        fontsize=9.0, pad=4,
    )
    ax.legend(fontsize=6.6, frameon=False, loc="lower right",
              handlelength=1.2, ncol=2)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
